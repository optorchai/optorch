"""ollama chunk extractor"""
import json
from optorch.logging import get_logger
from typing import Any, Optional, Dict, List
from optorch.llm.metrics import Usage

logger = get_logger(__name__)

class OllamaExtractor:
    """extract data from ollama chunk format"""
    
    @staticmethod
    def extract_content(chunk: Any) -> Optional[str]:
        if isinstance(chunk, dict):
            return chunk.get('message', {}).get('content', '')
        return None
    
    @staticmethod
    def extract_tool_calls(chunk: Any) -> Optional[Any]:
        if isinstance(chunk, dict):
            msg = chunk.get('message', {})
            if 'tool_calls' in msg and msg['tool_calls']:
                return msg['tool_calls']
        return None
    
    @staticmethod
    def extract_usage(chunk: Any, model: str) -> Optional[Usage]:
        if isinstance(chunk, dict) and chunk.get('done'):
            prompt_tokens = chunk.get('prompt_eval_count', 0)
            completion_tokens = chunk.get('eval_count', 0)
            return Usage(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=0.0
            )
        return None
    
    @staticmethod
    def create_tool_buffer() -> List[Dict[str, Any]]:
        return []
    
    @staticmethod
    def accumulate_tools(tool_calls: Any, buffer: List[Dict[str, Any]]) -> None:
        buffer.extend(tool_calls)
    
    @staticmethod
    def finalize_tools(buffer: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        complete_tools = []
        for tc in buffer:
            try:
                args = tc.get("function", {}).get("arguments", "")
                if args:
                    json.loads(args) if isinstance(args, str) else args
                complete_tools.append(tc)
            except json.JSONDecodeError:
                logger.warning(f"incomplete tool json: {tc.get('function', {}).get('name')}")
        return complete_tools
