"""On-demand search strategy"""

from typing import List, Optional
from optorch.messaging import Message, MessageContext
from .base import SearchStrategy


class OnDemandSearch(SearchStrategy):
    
    async def search(
        self,
        query: str,
        context: MessageContext,
        vector_search_func
    ) -> Optional[List[Message]]:
        if context.metadata.get("use_vector_search", False):
            return await vector_search_func(query, context)
        return None
