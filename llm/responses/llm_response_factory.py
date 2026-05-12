"""factory for creating llm responses"""
from typing import List, Dict, Any, Optional, AsyncIterator
from optorch.llm.responses.llm_response import LLMResponse
from optorch.llm.responses.standard_response import StandardLLMResponse
from optorch.llm.responses.streaming_response import StreamingLLMResponse
from optorch.llm.metrics import Usage

class LLMResponseFactory:
    """builds response objects - streaming or standard"""
    
    @staticmethod
    def create(
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        usage: Optional[Usage] = None,
        raw_response: Optional[Any] = None
    ) -> StandardLLMResponse:
        """standard response for non-streaming"""
        return StandardLLMResponse(
            _content=content,
            _tool_calls=tool_calls,
            _usage=usage,
            _raw_response=raw_response
        )
    
    @staticmethod
    def create_streaming(
        stream: AsyncIterator,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        usage: Optional[Usage] = None,
        raw_response: Optional[Any] = None
    ) -> StreamingLLMResponse:
        """streaming response with async iterator"""
        return StreamingLLMResponse(
            stream=stream,
            tool_calls=tool_calls,
            usage=usage,
            raw_response=raw_response
        )
