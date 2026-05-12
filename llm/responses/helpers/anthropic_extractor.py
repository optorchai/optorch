from optorch.logging import get_logger
from typing import Any, Optional, Dict, List, Tuple
from optorch.llm.metrics import Usage

logger = get_logger(__name__)

_MSG_START = "message_start"
_MSG_DELTA = "message_delta"
_BLOCK_START = "content_block_start"
_BLOCK_DELTA = "content_block_delta"


class AnthropicExtractor:
    """extract data from anthropic streaming event format"""

    @staticmethod
    def extract_content(chunk: Any) -> Optional[str]:
        if getattr(chunk, "type", None) == _BLOCK_DELTA:
            delta = getattr(chunk, "delta", None)
            if getattr(delta, "type", None) == "text_delta":
                return getattr(delta, "text", None)
        return None

    @staticmethod
    def extract_tool_calls(chunk: Any) -> Optional[Tuple[str, Any]]:
        """returns ('start', chunk) or ('delta', chunk) for tool-related events"""
        chunk_type = getattr(chunk, "type", None)

        if chunk_type == _BLOCK_START:
            cb = getattr(chunk, "content_block", None)
            if getattr(cb, "type", None) == "tool_use":
                return ("start", chunk)

        elif chunk_type == _BLOCK_DELTA:
            delta = getattr(chunk, "delta", None)
            if getattr(delta, "type", None) == "input_json_delta":
                return ("delta", chunk)

        return None

    @staticmethod
    def extract_usage(chunk: Any, model: str) -> Optional[Usage]:
        chunk_type = getattr(chunk, "type", None)

        # input tokens arrive in message_start
        if chunk_type == _MSG_START:
            msg = getattr(chunk, "message", None)
            usage = getattr(msg, "usage", None) if msg else None
            if usage:
                input_tokens = getattr(usage, "input_tokens", 0) or 0
                return Usage(
                    input_tokens=input_tokens,
                    output_tokens=0,
                    total_tokens=input_tokens,
                    cost=0.0,
                )

        # output tokens arrive in message_delta
        if chunk_type == _MSG_DELTA:
            usage = getattr(chunk, "usage", None)
            if usage:
                output_tokens = getattr(usage, "output_tokens", 0) or 0
                return Usage(
                    input_tokens=0,
                    output_tokens=output_tokens,
                    total_tokens=output_tokens,
                    cost=0.0,
                )

        return None

    @staticmethod
    def create_tool_buffer() -> Dict[int, Dict[str, Any]]:
        return {}

    @staticmethod
    def accumulate_tools(
        tool_calls: Tuple[str, Any],
        buffer: Dict[int, Dict[str, Any]],
    ) -> None:
        kind, chunk = tool_calls
        idx: int = getattr(chunk, "index", 0)

        if kind == "start":
            cb = chunk.content_block
            buffer[idx] = {
                "id": getattr(cb, "id", None),
                "type": "function",
                "function": {"name": getattr(cb, "name", ""), "arguments": ""},
            }
        elif kind == "delta":
            if idx in buffer:
                partial = getattr(chunk.delta, "partial_json", "")
                buffer[idx]["function"]["arguments"] += partial or ""

    @staticmethod
    def finalize_tools(buffer: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        from optorch.llm.responses.helpers.streaming import finalize_tool_calls
        return finalize_tool_calls(buffer) if buffer else []
