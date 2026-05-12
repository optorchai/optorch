"""Base search strategy"""

from abc import ABC, abstractmethod
from typing import List, Optional
from optorch.messaging import Message, MessageContext


class SearchStrategy(ABC):
    
    @abstractmethod
    async def search(
        self,
        query: str,
        context: MessageContext,
        vector_search_func
    ) -> Optional[List[Message]]:
        pass
