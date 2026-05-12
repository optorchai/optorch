"""Token budget memory strategy"""

from typing import List
from optorch.messaging import Message


class TokenBudget:
    
    def __init__(self, max_tokens: int = 4000) -> None:
        self.max_tokens = max_tokens
    
    def _estimate_tokens(self, message: Message) -> int:
        return len(message.content) // 4
    
    def get_messages(self, messages: List[Message]) -> List[Message]:
        result = []
        token_count = 0
        
        # Work backwards from newest
        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens(msg)
            
            if token_count + msg_tokens > self.max_tokens:
                break
            
            result.insert(0, msg)
            token_count += msg_tokens
        
        return result
