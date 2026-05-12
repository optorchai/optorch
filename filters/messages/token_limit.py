"""Truncate messages to stay within token limits"""
from typing import List, Dict, Any
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter


@register_filter("token_limit")
class TokenLimitFilter(BaseFilter):
    """Truncate messages to stay within token limits"""
    
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
    
    def filter(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply token limiting to messages"""
        if len(messages) > self.max_messages:
            return messages[-self.max_messages:]
        return messages