"""Async stream testing helpers"""

import asyncio
from typing import AsyncIterator, List, TypeVar, Any

T = TypeVar('T')


class AsyncStreamCollector:
    """Collects async stream items for testing"""
    
    def __init__(self):
        self.items: List[Any] = []
        self.completed = False
        self.error: Exception | None = None
    
    async def collect(self, stream: AsyncIterator[T], max_items: int = 100) -> List[T]:
        """Collect stream items up to max_items"""
        try:
            async for item in stream:
                self.items.append(item)
                if len(self.items) >= max_items:
                    break
            self.completed = True
        except Exception as e:
            self.error = e
        
        return self.items
    
    async def collect_with_timeout(
        self, 
        stream: AsyncIterator[T], 
        timeout: float = 5.0
    ) -> List[T]:
        """Collect stream items with timeout"""
        try:
            return await asyncio.wait_for(self.collect(stream), timeout)
        except asyncio.TimeoutError:
            return self.items


async def mock_async_generator(*items: T) -> AsyncIterator[T]:
    """Create mock async generator from items"""
    for item in items:
        yield item
        await asyncio.sleep(0)  # yield control