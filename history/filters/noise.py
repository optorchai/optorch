"""Noise filter for system spam"""

from typing import List, Optional
from optorch.messaging import Message
from .base import MessageFilter


class NoiseFilter(MessageFilter):
    
    def __init__(self, patterns: Optional[List[str]] = None) -> None:
        default_patterns = [
            "typing...",
            "is typing",
            "reconnecting",
            "connection lost",
            "connection restored"
        ]
        self.patterns = set(patterns or default_patterns)
    
    def filter(self, messages: List[Message]) -> List[Message]:
        filtered = []
        
        for msg in messages:
            is_noise = any(
                pattern.lower() in msg.content.lower()
                for pattern in self.patterns
            )
            
            if not is_noise:
                filtered.append(msg)
        
        return filtered
