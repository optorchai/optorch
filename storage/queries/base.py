from abc import ABC, abstractmethod
from typing import Any
from optorch.storage.store.base import AbstractStore


class BaseQuery(ABC):
    """base class for database queries"""
    
    def __init__(self, store: AbstractStore):
        self.store = store
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """execute query and return results"""
        pass
    
    @property
    @abstractmethod
    def query_name(self) -> str:
        """unique query identifier"""
        pass
