"""Filtered storage strategy"""

from typing import List
from optorch.messaging import Message, MessageContext, MessageSource
from optorch.history.filters import MessageFilter
from .base import StorageStrategy


class FilteredStorage(StorageStrategy):
    
    def __init__(self, source: MessageSource, filter: MessageFilter) -> None:
        self.source = source
        self.filter = filter
    
    async def save(self, messages: List[Message], context: MessageContext) -> None:
        if not messages:
            return
        
        # Apply filter
        filtered = self.filter.filter(messages)
        
        # Save filtered messages
        if filtered:
            await self.source.save(filtered, context)
    
    async def load(self, context: MessageContext) -> List[Message]:
        return await self.source.get(context)
