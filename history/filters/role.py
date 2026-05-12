"""Role-based message filter"""

from typing import List, Optional
from optorch.messaging import Message
from .base import MessageFilter


class RoleFilter(MessageFilter):
    
    def __init__(self, allowed_roles: Optional[List[str]] = None, blocked_roles: Optional[List[str]] = None) -> None:
        self.allowed_roles = set(allowed_roles) if allowed_roles else None
        self.blocked_roles = set(blocked_roles) if blocked_roles else set()
    
    def filter(self, messages: List[Message]) -> List[Message]:
        filtered = []
        
        for msg in messages:
            # Check blocked first
            if msg.role in self.blocked_roles:
                continue
            
            # Check allowed if specified
            if self.allowed_roles and msg.role not in self.allowed_roles:
                continue
            
            filtered.append(msg)
        
        return filtered
