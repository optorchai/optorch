"""Time-based message filter"""

from typing import List, Optional
from datetime import datetime
from optorch.messaging import Message
from .base import MessageFilter


class TimeRangeFilter(MessageFilter):
    
    def __init__(
        self,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None
    ):
        self.after = after
        self.before = before
    
    def filter(self, messages: List[Message]) -> List[Message]:
        filtered = []
        
        for msg in messages:
            # Check after bound
            if self.after and msg.timestamp < self.after:
                continue
            
            # Check before bound
            if self.before and msg.timestamp > self.before:
                continue
            
            filtered.append(msg)
        
        return filtered
