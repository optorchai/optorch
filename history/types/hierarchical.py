"""Hierarchical memory strategy"""

from typing import List
from optorch.messaging import Message


class Hierarchical:
    
    def __init__(
        self,
        immediate_count: int = 5,
        recent_count: int = 15,
        context_count: int = 10
    ):
        self.immediate_count = immediate_count
        self.recent_count = recent_count
        self.context_count = context_count
    
    def get_messages(self, messages: List[Message]) -> List[Message]:
        if not messages:
            return []
        
        total = len(messages)
        result = []
        
        # Immediate: Last N messages (always included)
        immediate_start = max(0, total - self.immediate_count)
        immediate = messages[immediate_start:]
        
        # Recent: Previous batch
        recent_end = immediate_start
        recent_start = max(0, recent_end - self.recent_count)
        recent = messages[recent_start:recent_end]
        
        # Context: Sampled from older messages
        context_end = recent_start
        if context_end > 0:
            # Sample evenly from older messages
            step = max(1, context_end // self.context_count)
            context = messages[0:context_end:step][:self.context_count]
        else:
            context = []
        
        # Combine: context + recent + immediate
        result = context + recent + immediate
        
        return result
