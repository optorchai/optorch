"""Threshold-based search strategy"""

from typing import List, Optional
from optorch.messaging import Message, MessageContext
from .base import SearchStrategy


class ThresholdSearch(SearchStrategy):
    
    def __init__(self, message_threshold: int = 50, token_threshold: int = 10000) -> None:
        self.message_threshold = message_threshold
        self.token_threshold = token_threshold
    
    async def search(
        self,
        query: str,
        context: MessageContext,
        vector_search_func
    ) -> Optional[List[Message]]:
        # Check message count threshold
        message_count = context.metadata.get("message_count", 0)
        if message_count >= self.message_threshold:
            return await vector_search_func(query, context)
        
        # Check token threshold
        token_count = context.metadata.get("token_count", 0)
        if token_count >= self.token_threshold:
            return await vector_search_func(query, context)
        
        return None
