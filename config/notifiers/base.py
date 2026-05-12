"""
Base for config change notification strategies
"""
from abc import ABC, abstractmethod
from typing import Callable


class ConfigChangeNotifier(ABC):
    """Base for config change notification strategies"""
    
    @abstractmethod
    def start(self, on_change: Callable[[], None]) -> None:
        """Start watching, call on_change when config changes"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop watching"""
        pass
