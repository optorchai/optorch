"""try providers until one works"""

from optorch.logging import get_logger
from typing import List

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.llm.manager import LLMManager
from optorch.events import EventTypes
from optorch.errors import error_context, ErrorAction

logger = get_logger(__name__)


class ProviderFallback(BaseLLMProcessor):
    """fallback providers on failure"""
    
    def __init__(self):
        super().__init__()
        self.substates = {"default", "retry"}
        self.exclude_substates = {"tool_result"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.INVOKE
    
    def _get_available_providers(self, context: LLMContext) -> List[str]:
        """get all registered providers or die trying"""
        if not context.node_context or not context.node_context.controller:
            raise ValueError("No controller available in context")
        
        registry = context.node_context.controller.llm.registry()
        clients = registry.list_clients()
        pools = registry.list_pools()
        available = clients + pools
        
        if not available:
            raise ValueError("No LLM providers registered - cant fallback to nothing")
        return available
    
    @error_context(component="llm", phase="fallback", default_action=ErrorAction.LOG_AND_RAISE)
    async def process(self, context: LLMContext) -> None:
        """try providers until success or exhausted"""
        if not context.messages:
            logger.debug("No messages for fallback - skipping")
            return
        
        fallback_config = context.config.get("fallback", {}) if context.config else {}
        providers = fallback_config.get("providers")
        
        if not providers or not isinstance(providers, list):
            providers = self._get_available_providers(context)
        
        if not context.node_context or not context.node_context.container.llm_manager:
            logger.warning("No LLMManager available - skipping fallback")
            return
            
        manager = context.node_context.container.llm_manager
        errors = []
        
        for i, provider_name in enumerate(providers):
            is_last = (i == len(providers) - 1)
            attempt_num = i + 1
            
            try:
                logger.debug(f"Provider attempt {attempt_num}/{len(providers)}: {provider_name}")
                
                if not context.node_context or not context.node_context.controller:
                    raise ValueError("No controller available in context")
                
                client = context.node_context.controller.llm.registry().get(provider_name)
                if not client:
                    raise ValueError(f"Provider '{provider_name}' not registered")
                
                if context.streaming:
                    response = await client.astream(
                        context,
                        context.messages,
                        **context.config.get("invoke_kwargs", {}) if context.config else {}
                    )
                else:
                    response = await client.invoke(
                        context,
                        context.messages,
                        **context.config.get("invoke_kwargs", {}) if context.config else {}
                    )
                
                context.response = response  # finally something worked
                
                if attempt_num > 1:
                    logger.info(f"Provider fallback SUCCESS: {provider_name} (attempt {attempt_num})")
                    context.events.emit(EventTypes.LLM, {
                        "event": "fallback_success",
                        "provider": provider_name,
                        "attempt": attempt_num,
                        "previous_errors": errors
                    })
                else:
                    logger.debug(f"Primary provider SUCCESS: {provider_name}")
                
                return
                
            except Exception as e:
                error_msg = str(e)
                errors.append({"provider": provider_name, "error": error_msg})
                logger.warning(f"Provider {provider_name} failed: {e}")
                
                context.events.emit(EventTypes.LLM, {
                    "event": "fallback_attempt",
                    "provider": provider_name,
                    "attempt": attempt_num,
                    "error": error_msg,
                    "is_last": is_last
                })
                
                if is_last:
                    context.events.emit(EventTypes.LLM, {
                        "event": "fallback_exhausted", 
                        "providers": providers,
                        "errors": errors
                    })
                    raise Exception(f"All fallback providers failed: {[e['error'] for e in errors]}") from e