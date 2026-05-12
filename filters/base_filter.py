"""Base filter class for all filters"""
from abc import ABC, abstractmethod
from typing import Any


class BaseFilter(ABC):
    """Base class for all filters"""
    
    @abstractmethod
    def filter(self, data: Any) -> Any:
        """Apply filter to data"""
        pass
    
    def __call__(self, data: Any) -> Any:
        return self.filter(data)