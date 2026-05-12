"""Hybrid storage strategy"""

from typing import List
from optorch.messaging import Message, MessageContext, MessageSource
from optorch.history.filters import MessageFilter
from .base import StorageStrategy


class HybridStorage(StorageStrategy):
    
    def __init__(
        self,
        source: MessageSource,
        filter: MessageFilter,
        summarizer_func,
        recent_count: int = 20
    ):
        self.source = source
        self.filter = filter
        self.summarizer = summarizer_func
        self.recent_count = recent_count
    
    async def save(self, messages: List[Message], context: MessageContext) -> None:
        if not messages:
            return
        
        # Split into recent and old
        recent = messages[-self.recent_count:] if len(messages) > self.recent_count else messages
        old = messages[:-self.recent_count] if len(messages) > self.recent_count else []
        
        to_save = []
        
        # Summarize old messages
        if old:
            summary_text = await self.summarizer(old)
            summary = Message(
                role="system",
                content=summary_text,
                metadata={
                    "is_summary": True,
                    "original_count": len(old)
                }
            )
            to_save.append(summary)
        
        # Filter recent messages
        if recent:
            filtered_recent = self.filter.filter(recent)
            to_save.extend(filtered_recent)
        
        # Save combined result
        if to_save:
            await self.source.save(to_save, context)
    
    async def load(self, context: MessageContext) -> List[Message]:
        return await self.source.get(context)
