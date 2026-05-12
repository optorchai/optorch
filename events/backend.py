"""Abstract base for event backends"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set


class EventBackend(ABC):
    """Execution environment for event listeners"""
    
    def __init__(self, accept_tags: Optional[Set[str]] = None):
        self.accept_tags = accept_tags or set()
    
    @abstractmethod
    def notify(self, listeners: List[Any], event_type: str, event: Dict[str, Any]) -> None:
        """execute or publish event to assigned listeners"""
        pass
    
    async def close(self) -> None:
        """cleanup backend resources - override for connection cleanup"""
        pass
