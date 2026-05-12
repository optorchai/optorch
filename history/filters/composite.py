"""Composite filter for combining filters"""

from typing import List
from optorch.messaging import Message
from .base import MessageFilter


class CompositeFilter(MessageFilter):
    
    def __init__(self, filters: List[MessageFilter]) -> None:
        self.filters = filters
    
    def filter(self, messages: List[Message]) -> List[Message]:
        result = messages
        for f in self.filters:
            result = f.filter(result)
        return result
    
    def add(self, filter: MessageFilter):
        self.filters.append(filter)
