"""standard non-streaming response"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from optorch.llm.responses.llm_response import LLMResponse
from optorch.llm.metrics import Usage
from optorch.transformers.base_transformer import BaseTransformer

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext

@dataclass
class StandardLLMResponse(LLMResponse):
    """standard response for non-streaming calls"""
    _content: Optional[str] = None
    _tool_calls: Optional[List[Dict[str, Any]]] = None
    _usage: Optional[Usage] = None
    _raw_response: Optional[Any] = None
    _metadata: Optional[Dict[str, Any]] = None
    
    @property
    def is_stream(self) -> bool:
        return False
    
    @property
    def content(self) -> Optional[str]:
        return self._content
    
    @property
    def tool_calls(self) -> Optional[List[Dict[str, Any]]]:
        return self._tool_calls
    
    @property
    def usage(self) -> Optional[Usage]:
        return self._usage
    
    @property
    def raw_response(self) -> Optional[Any]:
        return self._raw_response
    
    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        return self._metadata
    
    async def apply_transformers(self, transformers: List[BaseTransformer], context: 'LLMContext') -> 'StandardLLMResponse':
        """apply transformers to content, return new response with transformed content"""
        if not transformers or not self._content:
            return self
        
        content = self._content
        metadata = {}
        
        for transformer in transformers:
            result = await transformer.transform(content, context)
            content = result.get("content", content)
            if "metadata" in result:
                metadata.update(result["metadata"])
        
        return StandardLLMResponse(
            _content=content,
            _tool_calls=self._tool_calls,
            _usage=self._usage,
            _raw_response=self._raw_response,
            _metadata=metadata if metadata else None
        )
