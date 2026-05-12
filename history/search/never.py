"""Never search strategy"""

from typing import List, Optional
from optorch.messaging import Message, MessageContext
from .base import SearchStrategy


class NeverSearch(SearchStrategy):
    
    async def search(
        self,
        query: str,
        context: MessageContext,
        vector_search_func
    ) -> Optional[List[Message]]:
        return None
