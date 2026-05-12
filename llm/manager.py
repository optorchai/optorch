"""LLM Manager - Client pooling, model routing, lifecycle orchestration"""

from typing import Dict, Optional, Any, cast, TYPE_CHECKING, Protocol
from decimal import Decimal
from optorch.logging import get_logger

from optorch.llm.lifecycle.executor import LLMLifecycleExecutor
from optorch.llm.lifecycle.context import LLMContext
from optorch.llm.lifecycle.context_factory import LLMContextFactory
from optorch.llm.base_client import BaseLLMClient
from optorch.llm.responses import LLMResponse
from optorch.llm.responses.streaming_response import StreamingLLMResponse
from optorch.state.base_state import BaseState

if TYPE_CHECKING:
    from optorch.events.event_emitter import EventEmitter
    from optorch.controller.node_context import NodeContext

logger = get_logger(__name__)


class LLMRegistryProtocol(Protocol):
    """Protocol for LLM registry - defines minimal interface needed by LLMManager"""
    def get(self, name: str) -> Optional[BaseLLMClient]: ...


class LLMManager:
    """Managing LLM clients, model routing, and lifecycle execution
    
    Responsibilities:
    - Model routing via registry
    - Lifecycle orchestration via executor
    - Budget cascade resolution
    - State integration
    """
    
    def __init__(self):
        self._executor = LLMLifecycleExecutor()
        self._config: Optional[Dict] = None
        self._llm_registry: Optional[LLMRegistryProtocol] = None
        
        logger.debug("LLMManager initialized")
    
    def set_config(self, llm_config: Dict) -> None:
        self._config = llm_config

    def set_llm_registry(self, llm_registry: LLMRegistryProtocol) -> None:
        self._llm_registry = llm_registry
    
    def get_client(self, model: str) -> BaseLLMClient:
        if not self._llm_registry:
            from optorch.errors.exceptions import ConfigurationError
            raise ConfigurationError("LLM registry not set in LLMManager - call set_llm_registry() first")
        
        client = self._llm_registry.get(model)
        if client is None:
            from optorch.errors.exceptions import LLMError
            raise LLMError(f"Model/LLM '{model}' not found in registry", model=model)
        
        return client
    
    def _resolve_budget(self, invoke_budget: Optional[Decimal], config: Dict[str, Any]) -> Optional[Decimal]:
        """Resolve budget from cascade: invoke > node > phase > global
        
        Args:
            invoke_budget: Budget passed to invoke()
            config: Config dict with potential budget values
            
        Returns:
            Resolved budget or None
        """
        if invoke_budget is not None:
            return invoke_budget
        
        if config.get("node_budget"):
            return Decimal(str(config["node_budget"]))
        
        if config.get("phase_budget"):
            return Decimal(str(config["phase_budget"]))
        
        if config.get("global_budget"):
            return Decimal(str(config["global_budget"]))
        
        return None
    
    def _prepare_context(
        self,
        model: str,
        messages: list,
        config: Optional[Dict[str, Any]],
        state: Optional[BaseState],
        budget: Optional[Decimal],
        event_emitter: Optional['EventEmitter'],
        node_context: Optional['NodeContext'],
        context: Optional[LLMContext],
        streaming: bool,
        **kwargs
    ) -> tuple[LLMContext, 'EventEmitter']:
        config = config or {}
        if self._config:
            config = {**self._config, **config}
        config["invoke_kwargs"] = kwargs

        client = self.get_client(model)
        if not config.get("model") and client.model:
            config["model"] = client.model

        if not event_emitter:
            from optorch.events import EventEmitter
            event_emitter = EventEmitter()

        ctx = LLMContextFactory.populate(
            context=context,
            events=event_emitter,
            client=client,
            messages=list(messages),
            config=config,
            state=state,
            budget=self._resolve_budget(budget, config),
            streaming=streaming,
            node_context=node_context
        )
        return ctx, event_emitter

    async def invoke(
        self,
        model: str,
        messages: list,
        config: Optional[Dict[str, Any]] = None,
        state: Optional[BaseState] = None,
        budget: Optional[Decimal] = None,
        event_emitter: Optional['EventEmitter'] = None,
        node_context: Optional['NodeContext'] = None,
        context: Optional[LLMContext] = None,
        **kwargs
    ) -> LLMResponse:
        context, event_emitter = self._prepare_context(
            model=model, messages=messages, config=config, state=state,
            budget=budget, event_emitter=event_emitter, node_context=node_context,
            context=context, streaming=False, **kwargs
        )
        try:
            context = await self._executor.execute(context, self._config)
            if not context.response:
                raise RuntimeError("Lifecycle did not produce response")
            return context.response
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}", exc_info=True)
            from optorch.events import EventTypes
            event_emitter.emit(EventTypes.ERROR, {
                "error": str(e),
                "error_type": type(e).__name__,
                "severity": "high",
                "component": "llm",
                "phase": "invoke"
            })
            raise

    async def astream(
        self,
        model: str,
        messages: list,
        config: Optional[Dict[str, Any]] = None,
        state: Optional[BaseState] = None,
        budget: Optional[Decimal] = None,
        event_emitter: Optional['EventEmitter'] = None,
        node_context: Optional['NodeContext'] = None,
        context: Optional[LLMContext] = None,
        **kwargs
    ) -> StreamingLLMResponse:
        context, event_emitter = self._prepare_context(
            model=model, messages=messages, config=config, state=state,
            budget=budget, event_emitter=event_emitter, node_context=node_context,
            context=context, streaming=True, **kwargs
        )
        try:
            context = await self._executor.execute(context, self._config)
            if not context.response:
                raise RuntimeError("Lifecycle did not produce response")
            return cast(StreamingLLMResponse, context.response)
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}", exc_info=True)
            from optorch.events import EventTypes
            event_emitter.emit(EventTypes.ERROR, {
                "error": str(e),
                "error_type": type(e).__name__,
                "severity": "high",
                "component": "llm",
                "phase": "stream"
            })
            raise
    
    async def embed(
        self,
        texts: list[str],
        model: str = "text-embedding-3-small",
        event_emitter: Optional['EventEmitter'] = None
    ) -> list[list[float]]:
        """Generate embeddings with cost tracking and event emission
        
        Routes through embedding provider but emits cost events like LLM calls.
        
        Args:
            texts: Texts to embed
            model: Embedding model name
            event_emitter: EventEmitter for cost tracking
            
        Returns:
            List of embedding vectors
        """
        from optorch.embeddings.embeddings_registry import EmbeddingsRegistry
        from optorch.llm.metrics.usage import Usage
        from optorch.constants import EventTypes
        from optorch.events.decorators import emits
        
        if not event_emitter:
            from optorch.events import EventEmitter
            event_emitter = EventEmitter()
        
        # get embedding provider
        registry = EmbeddingsRegistry()
        provider = registry.get(model)
        
        if not provider:
            from optorch.embeddings.providers.openai_provider import OpenAIEmbeddingProvider
            provider = OpenAIEmbeddingProvider(model=model)
        
        try:
            embeddings = await provider.embed(texts)
            
            # calculate cost (embeddings charged per token, not per call)
            from optorch.llm.pricing import Pricing
            
            # rough token estimate: ~1 token per 4 characters
            total_chars = sum(len(text) for text in texts)
            estimated_tokens = total_chars // 4
            
            usage = Usage.create(
                model=model,
                input_tokens=estimated_tokens,
                output_tokens=0,  # embeddings have no output tokens
                currency="usd"
            )
            
            # detect provider from class name
            provider_name = type(provider).__name__.lower().replace("embeddingprovider", "").replace("provider", "")
            
            # emit cost event
            event_data = {
                "cost": usage.cost,
                "model": model,
                "provider": provider_name,
                "input_tokens": usage.input_tokens,
                "total_tokens": usage.total_tokens,
                "text_count": len(texts),
                "operation": "embed"
            }
            
            event_emitter.emit(f"{EventTypes.EMBEDDING}.cost", event_data)
            logger.info(f"Embedding cost: ${usage.cost:.6f} for {len(texts)} texts ({usage.input_tokens} tokens)")
            
            return embeddings
        
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}", exc_info=True)
            
            event_emitter.emit(EventTypes.ERROR, {
                "error": str(e),
                "error_type": type(e).__name__,
                "severity": "medium",
                "component": "llm_manager",
                "operation": "embed",
                "model": model
            })
            
            raise
    
    @property
    def executor(self) -> LLMLifecycleExecutor:
        """Access lifecycle executor for processor registration"""
        return self._executor
