"""Filter registry"""

from typing import Dict, Type
from optorch.registry import Registry
from .base import MessageFilter


class FilterRegistry(Registry[Type[MessageFilter]]):
    
    def create(self, name: str, **kwargs) -> MessageFilter:
        if not self.has(name):
            raise ValueError(f"Unknown filter: {name}")
        filter_class = self.get(name)
        return filter_class(**kwargs)
