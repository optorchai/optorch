"""Base message filter"""

from abc import ABC, abstractmethod
from typing import List
from optorch.messaging import Message


class MessageFilter(ABC):
    
    @abstractmethod
    def filter(self, messages: List[Message]) -> List[Message]:
        pass
    
    def __call__(self, messages: List[Message]) -> List[Message]:
        return self.filter(messages)
