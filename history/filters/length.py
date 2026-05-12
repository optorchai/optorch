"""Length-based message filter"""

from typing import List
from optorch.messaging import Message
from .base import MessageFilter


class LengthFilter(MessageFilter):
    
    def __init__(self, min_length: int = 0, max_length: int = 100000) -> None:
        self.min_length = min_length
        self.max_length = max_length
    
    def filter(self, messages: List[Message]) -> List[Message]:
        return [
            msg for msg in messages
            if self.min_length <= len(msg.content) <= self.max_length
        ]
