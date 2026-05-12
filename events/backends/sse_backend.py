"""SSE backend for streaming events to browser"""
from typing import Dict, Any, List, Optional, Set, Callable
from optorch.events.backend import EventBackend
from optorch.events.listener_entry import ListenerEntry


class SSEBackend(EventBackend):
    """streams events to browser via callback"""
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'SSEBackend':
        """create from config - SSE backend requires runtime callback, use no-op for config instantiation"""
        def noop_callback(event: Dict[str, Any]) -> None:
            pass
        return cls(callback=noop_callback)
    
    def __init__(self, callback: Callable[[Dict[str, Any]], None], accept_tags: Optional[Set[str]] = None):
        super().__init__(accept_tags)
        self.callback = callback
    
    def notify(self, listeners: List[ListenerEntry], event_type: str, event: Dict[str, Any]) -> None:
        """call SSE callback with event"""
        try:
            self.callback(event)
        except Exception as e:
            from optorch.logging import get_logger
            get_logger(__name__).error(f"SSE callback failed: {e}")
