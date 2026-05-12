"""Summary storage strategy"""

from typing import Any, List, Optional
from optorch.messaging import Message, MessageContext, MessageSource
from .base import StorageStrategy


class SummaryStorage(StorageStrategy):
    
    def __init__(self, source: MessageSource, summarizer_func: Any) -> None:
        self.source = source
        self.summarizer = summarizer_func
    
    async def save(self, messages: List[Message], context: MessageContext) -> None:
        if not messages:
            return
        
        # Generate summary
        summary_text = await self.summarizer(messages)
        
        # Create summary message
        summary = Message(
            role="system",
            content=summary_text,
            metadata={
                "is_summary": True,
                "original_count": len(messages),
                "time_range": {
                    "start": messages[0].timestamp.isoformat(),
                    "end": messages[-1].timestamp.isoformat()
                }
            }
        )
        
        # Save single summary instead of all messages
        await self.source.save([summary], context)
    
    async def load(self, context: MessageContext) -> List[Message]:
        return await self.source.get(context)
