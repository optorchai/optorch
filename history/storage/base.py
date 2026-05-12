"""Base storage strategy"""

from abc import ABC, abstractmethod
from typing import List
from optorch.messaging import Message, MessageContext


class StorageStrategy(ABC):
    
    @abstractmethod
    async def save(self, messages: List[Message], context: MessageContext) -> None:
        pass
    
    @abstractmethod
    async def load(self, context: MessageContext) -> List[Message]:
        pass
