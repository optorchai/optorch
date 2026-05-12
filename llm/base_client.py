"""
Base LLM client interface for single clients and pools.
All LLM implementations must extend this class.
"""
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Optional, TYPE_CHECKING
from optorch.llm.responses import LLMResponse, StreamingLLMResponse, StandardLLMResponse, LLMResponseFactory
from optorch.llm.metrics import Usage

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext


class BaseLLMClient(ABC):
    """
    Base interface for all LLM clients (single or pooled).
    Provides transparent handling of single vs batch requests.
    
    Subclasses should define MODEL_PATTERNS for auto-detection:
        MODEL_PATTERNS: ClassVar[List[str]] = ["gpt-", "o1-", ...]
    """
    
    MODEL_PATTERNS: ClassVar[List[str]] = []
    
    def __init__(self, model: Optional[str] = None, tpm_limit: int = 90000, provider_prefix: Optional[str] = None) -> None:
        self.model = model
        self.tpm_limit = tpm_limit
        self.provider_prefix = provider_prefix
        self.active_requests = 0
    
    @abstractmethod
    async def invoke(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StandardLLMResponse:
        """
        Process single request.
        
        Args:
            messages: Chat messages in OpenAI format
            **kwargs: Provider-specific parameters (temperature, tools, etc.)
        
        Returns:
            LLMResponse with content, tool_calls, usage
        """
        pass
    
    @abstractmethod
    async def astream(self, context: 'LLMContext', messages: List[Dict[str, Any]], **kwargs) -> StreamingLLMResponse:
        """
        Stream response with async iterator.
        
        Args:
            messages: Chat messages in OpenAI format
            **kwargs: Provider-specific parameters (temperature, tools, etc.)
        
        Returns:
            StreamingLLMResponse with async iterator for content chunks
        """
        pass
    
    async def invoke_batch(self, context: 'LLMContext', message_batches: List[List[Dict[str, Any]]], **kwargs) -> List[LLMResponse]:
        """
        Process multiple requests. Default implementation is sequential.
        Pools override this for parallel processing with auto-detection.
        
        Args:
            context: LLM execution context
            message_batches: List of message arrays to process
            **kwargs: Provider-specific parameters
        
        Returns:
            List of LLMResponse objects in same order
        """
        results = []
        for messages in message_batches:
            result = await self.invoke(context, messages, **kwargs)
            results.append(result)
        return results
    
    async def raw_invoke(self, messages: List[Dict[str, Any]], **kwargs) -> StandardLLMResponse:
        """Direct API call - bypasses lifecycle processors"""
        self.active_requests += 1
        
        try:
            temperature = kwargs.pop('temperature', getattr(self, 'temperature', 0.7))
            tools = kwargs.pop('tools', None)
            
            params = await self._build_invoke_params(messages, temperature, tools, **kwargs)
            response = await self._call_api(params)
            
            return LLMResponseFactory.create(
                content=self._extract_content(response),
                tool_calls=self._extract_tool_calls(response),
                usage=self._extract_usage(response),
                raw_response=response
            )
        finally:
            self.active_requests -= 1
    
    async def raw_astream(self, messages: List[Dict[str, Any]], **kwargs) -> StreamingLLMResponse:
        """Direct streaming call - bypasses lifecycle processors"""
        self.active_requests += 1
        
        try:
            temperature = kwargs.pop('temperature', getattr(self, 'temperature', 0.7))
            tools = kwargs.pop('tools', None)
            budget = kwargs.pop('budget', None)
            
            if 'completion_type' not in kwargs:
                completion_type = getattr(self, 'completion_type', 'hard_stop')
            else:
                completion_type = kwargs.pop('completion_type')
            
            params = await self._build_stream_params(messages, temperature, tools, **kwargs)
            stream = await self._call_stream_api(params)
            
            return StreamingLLMResponse(
                stream=stream,
                model=self.model,
                provider=self._get_provider_name(),
                metadata={
                    "temperature": temperature,
                    "tools": tools is not None
                },
                budget=budget,
                completion_type=completion_type
            )
        finally:
            self.active_requests -= 1
    
    @abstractmethod
    async def _build_invoke_params(self, messages: List[Dict[str, Any]], temperature: float, tools: Optional[List], **kwargs) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def _build_stream_params(self, messages: List[Dict[str, Any]], temperature: float, tools: Optional[List], **kwargs) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def _call_api(self, params: Dict[str, Any]) -> Any:
        pass
    
    @abstractmethod
    async def _call_stream_api(self, params: Dict[str, Any]) -> Any:
        pass
    
    @abstractmethod
    def _extract_content(self, response: Any) -> str:
        pass
    
    @abstractmethod
    def _extract_tool_calls(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        pass
    
    @abstractmethod
    def _extract_usage(self, response: Any) -> Optional[Usage]:
        pass
    
    @abstractmethod
    def _get_provider_name(self) -> str:
        pass
    
    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Rough token estimation (4 chars = 1 token)"""
        text = str(messages)
        return len(text) // 4
    
    def get_effective_tpm(self) -> int:
        """Get effective TPM for this client/pool"""
        return self.tpm_limit
    
    def __repr__(self):
        return f"{self.__class__.__name__}(model={self.model})"
