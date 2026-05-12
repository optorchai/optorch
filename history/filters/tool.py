"""Tool call filter"""

from typing import List
from optorch.messaging import Message
from .base import MessageFilter


class ToolFilter(MessageFilter):
    
    def __init__(self, keep_tool_calls: bool = True, keep_tool_results: bool = True) -> None:
        self.keep_tool_calls = keep_tool_calls
        self.keep_tool_results = keep_tool_results
    
    def filter(self, messages: List[Message]) -> List[Message]:
        filtered = []
        
        for msg in messages:
            is_tool_call = msg.metadata.get("is_tool_call", False)
            is_tool_result = msg.metadata.get("is_tool_result", False)
            
            # Skip tool calls if not keeping
            if is_tool_call and not self.keep_tool_calls:
                continue
            
            # Skip tool results if not keeping
            if is_tool_result and not self.keep_tool_results:
                continue
            
            filtered.append(msg)
        
        return filtered
