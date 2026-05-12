"""helpers for streaming response processing - shared logic"""
import json
from optorch.logging import get_logger
from decimal import Decimal
from typing import Dict, List, Any, Optional
from optorch.llm.budget import Pricing, BaseCompletionType

logger = get_logger(__name__)

def accumulate_tool_calls(delta_tools: List[Any], buffer: Dict[int, Dict]) -> None:
    """accumulate tool calls from delta chunks into buffer"""
    for delta_tool in delta_tools:
        idx = delta_tool.index
        
        if idx not in buffer:
            buffer[idx] = {
                "id": getattr(delta_tool, 'id', None),
                "type": getattr(delta_tool, 'type', 'function'),
                "function": {"name": "", "arguments": ""}
            }
        
        if hasattr(delta_tool, 'id') and delta_tool.id:
            buffer[idx]["id"] = delta_tool.id
        
        if hasattr(delta_tool, 'function'):
            func = delta_tool.function
            if hasattr(func, 'name') and func.name:
                buffer[idx]["function"]["name"] = func.name
            if hasattr(func, 'arguments') and func.arguments:
                buffer[idx]["function"]["arguments"] += func.arguments


def finalize_tool_calls(buffer: Dict[int, Dict]) -> List[Dict[str, Any]]:
    """convert tool call buffer to final list"""
    if not buffer:
        return []
    
    calls = []
    for idx in sorted(buffer.keys()):
        tool = buffer[idx]
        try:
            if tool["function"]["arguments"]:
                tool["function"]["arguments"] = json.loads(tool["function"]["arguments"])
        except json.JSONDecodeError:
            logger.warning(f"failed to parse tool args: {tool['function']['arguments']}")
        calls.append(tool)
    
    return calls

def check_budget_exceeded(
    chunk_tokens: int,
    model: str,
    total_tokens: int,
    total_cost: Decimal,
    budget: Decimal,
    completion_type: BaseCompletionType,
    content_buffer: str
) -> tuple[bool, Decimal, str]:
    """
    check if budget exceeded and handle completion type logic.
    
    returns: (should_stop, updated_cost, final_content)
    """
    chunk_cost = Pricing.cost_per_chunk(model, chunk_tokens, is_completion=True)
    updated_cost = total_cost + chunk_cost
    
    if completion_type.should_stop(updated_cost, budget, total_tokens):
        final = completion_type.finalize(content_buffer)
        return True, updated_cost, final or ""
    
    return False, updated_cost, ""

def should_yield_chunk(
    delta_content: str,
    content_buffer: str,
    completion_type: Optional[BaseCompletionType]
) -> tuple[bool, str]:
    """
    determine if chunk should be yielded based on completion type.
    
    returns: (should_yield, updated_buffer)
    """
    if completion_type:
        return completion_type.should_yield(delta_content, content_buffer)
    else:
        return True, delta_content

def emit_chunk_event(content: str, cost: Decimal, tokens: int) -> None:
    """emit llm chunk event - disabled for streaming optimization
    
    event emission in streaming disabled to reduce overhead
    full LLM lifecycle events still emitted at completion
    """
    pass
