"""
Disabled watcher - production default
"""
from typing import Callable
from optorch.config.notifiers.base import ConfigChangeNotifier


class NoOpNotifier(ConfigChangeNotifier):
    """Disabled watcher - production default"""
    
    def start(self, on_change: Callable[[], None]) -> None:
        pass
    
    def stop(self) -> None:
        pass
