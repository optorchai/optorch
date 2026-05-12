"""Error message filter"""

from typing import List
from optorch.messaging import Message
from .base import MessageFilter


class ErrorFilter(MessageFilter):
    
    def __init__(self, keep_errors: bool = False) -> None:
        self.keep_errors = keep_errors
    
    def filter(self, messages: List[Message]) -> List[Message]:
        if self.keep_errors:
            return messages
        
        return [
            msg for msg in messages
            if not msg.metadata.get("is_error", False)
            and "error" not in msg.role.lower()
        ]
