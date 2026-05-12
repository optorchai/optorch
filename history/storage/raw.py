"""Raw storage strategy"""

from typing import List
from optorch.messaging import Message, MessageContext, MessageSource
from .base import StorageStrategy


class RawStorage(StorageStrategy):
    
    def __init__(self, source: MessageSource) -> None:
        self.source = source
    
    async def save(self, messages: List[Message], context: MessageContext) -> None:
        if messages:
            await self.source.save(messages, context)
    
    async def load(self, context: MessageContext) -> List[Message]:
        return await self.source.get(context)
