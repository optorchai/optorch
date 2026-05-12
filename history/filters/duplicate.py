"""Duplicate message filter"""

from typing import List, Set
from optorch.messaging import Message
from .base import MessageFilter


class DuplicateFilter(MessageFilter):
    
    def __init__(self, by_content: bool = True, by_id: bool = False) -> None:
        self.by_content = by_content
        self.by_id = by_id
    
    def filter(self, messages: List[Message]) -> List[Message]:
        seen: Set[str] = set()
        filtered = []
        
        for msg in messages:
            key = None
            if self.by_id:
                key = msg.id
            elif self.by_content:
                key = f"{msg.role}:{msg.content}"
            
            if key and key in seen:
                continue
            
            if key:
                seen.add(key)
            filtered.append(msg)
        
        return filtered
