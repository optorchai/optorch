"""openai/groq chunk extractor"""
from typing import Any, Optional, Dict, List
from optorch.llm.metrics import Usage

class OpenAIExtractor:
    """extract data from openai/groq chunk format"""
    
    @staticmethod
    def extract_content(chunk: Any) -> Optional[str]:
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content:
                return delta.content
        return None
    
    @staticmethod
    def extract_tool_calls(chunk: Any) -> Optional[Any]:
        if hasattr(chunk, 'choices') and chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'tool_calls') and delta.tool_calls:
                return delta.tool_calls
        return None
    
    @staticmethod
    def extract_usage(chunk: Any, model: str) -> Optional[Usage]:
        if hasattr(chunk, 'usage') and chunk.usage:
            return Usage.create(
                model,
                chunk.usage.prompt_tokens,
                chunk.usage.completion_tokens
            )
        return None
    
    @staticmethod
    def create_tool_buffer() -> Dict[int, Dict[str, Any]]:
        return {}
    
    @staticmethod
    def accumulate_tools(tool_calls: Any, buffer: Dict[int, Dict[str, Any]]) -> None:
        from optorch.llm.responses.helpers import accumulate_tool_calls
        accumulate_tool_calls(tool_calls, buffer)
    
    @staticmethod
    def finalize_tools(buffer: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        from optorch.llm.responses.helpers import finalize_tool_calls
        return finalize_tool_calls(buffer) if buffer else []
