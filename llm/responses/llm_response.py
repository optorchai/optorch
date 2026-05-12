"""base llm response"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, TYPE_CHECKING, AsyncIterator
from optorch.llm.metrics import Usage
from optorch.transformers.base_transformer import BaseTransformer

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext

class LLMResponse(ABC):
    """abstract base for llm responses"""
    
    _response_id: Optional[str] = None
    
    @property
    def response_id(self) -> Optional[str]:
        return self._response_id
    
    @property
    @abstractmethod
    def is_stream(self) -> bool:
        """whether this is a streaming response"""
        pass
    
    @property
    @abstractmethod
    def content(self) -> Optional[str]:
        pass
    
    @property
    @abstractmethod
    def tool_calls(self) -> Optional[List[Dict[str, Any]]]:
        pass
    
    @property
    @abstractmethod
    def usage(self) -> Optional[Usage]:
        pass
    
    @property
    @abstractmethod
    def raw_response(self) -> Optional[Any]:
        pass
    
    @property
    @abstractmethod
    def metadata(self) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def apply_transformers(self, transformers: List[BaseTransformer], context: 'LLMContext') -> 'LLMResponse':
        """apply transformers to content, return new response (preserves type)"""
        pass
    
    def set_tool_executor(self, callback: Callable) -> None:
        """inject tool executor callback - only implemented for streaming responses"""
        pass
    
    def set_context(self, context: 'LLMContext') -> None:
        """store context reference - only implemented for streaming responses"""
        pass
    
    @property
    def stream(self) -> AsyncIterator[str]:
        """access stream - only implemented for streaming responses"""
        raise NotImplementedError("stream property only available on StreamingLLMResponse")
