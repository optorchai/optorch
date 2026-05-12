"""Message source abstraction"""

from abc import ABC, abstractmethod
from typing import List
from .message import Message
from .context import MessageContext


class MessageSource(ABC):
    
    @abstractmethod
    async def get(self, context: MessageContext) -> List[Message]:
        pass
    
    @abstractmethod
    async def save(self, messages: List[Message], context: MessageContext) -> None:
        pass
