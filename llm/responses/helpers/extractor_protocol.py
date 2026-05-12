"""extractor protocol for type safety"""
from typing import Protocol, Any, Optional, Union, Dict, List
from optorch.llm.metrics import Usage

ToolBuffer = Union[Dict[int, Dict[str, Any]], List[Dict[str, Any]]]

class StreamExtractor(Protocol):
    """protocol for provider-specific chunk extractors"""
    
    @staticmethod
    def extract_content(chunk: Any) -> Optional[str]:
        ...
    
    @staticmethod
    def extract_tool_calls(chunk: Any) -> Optional[Any]:
        ...
    
    @staticmethod
    def extract_usage(chunk: Any, model: str) -> Optional[Usage]:
        ...
    
    @staticmethod
    def create_tool_buffer() -> ToolBuffer:
        ...
    
    @staticmethod
    def accumulate_tools(tool_calls: Any, buffer: ToolBuffer) -> None:
        ...
    
    @staticmethod
    def finalize_tools(buffer: ToolBuffer) -> List[Dict[str, Any]]:
        ...
