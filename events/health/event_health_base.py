"""Abstract base for health tracking"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class EventHealthBase(ABC):
    """Abstract interface for backend health tracking"""
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """check if backend is healthy"""
        pass
    
    @abstractmethod
    def success(self) -> None:
        """record successful operation"""
        pass
    
    @abstractmethod
    def error(self, exception: Exception) -> None:
        """record failed operation"""
        pass
    
    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """get health statistics"""
        pass
