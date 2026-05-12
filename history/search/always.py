"""Always search strategy"""

from typing import List, Optional
from optorch.messaging import Message, MessageContext
from .base import SearchStrategy


class AlwaysSearch(SearchStrategy):
    
    async def search(
        self,
        query: str,
        context: MessageContext,
        vector_search_func
    ) -> Optional[List[Message]]:
        return await vector_search_func(query, context)
