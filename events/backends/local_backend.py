"""Local in-process backend"""
from typing import Dict, Any, List
import asyncio
from optorch.logging import get_logger
from optorch.events.backend import EventBackend

logger = get_logger(__name__)


class LocalBackend(EventBackend):
    """Executes listeners in-process"""
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'LocalBackend':
        """create from config - local backend has no config options"""
        return cls()
    
    async def _safe_notify(self, listener: Any, event: Dict[str, Any]):
        """safe async execution"""
        try:
            if hasattr(listener, 'on_event'):
                if asyncio.iscoroutinefunction(listener.on_event):
                    await listener.on_event(event)
                else:
                    listener.on_event(event)
            elif callable(listener):
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
        except Exception as e:
            logger.error(f"Listener {listener} failed: {e}", exc_info=True)
    
    def notify(self, listeners: List[Any], event_type: str, event: Dict[str, Any]) -> None:
        """execute listeners - blocking sequential, async concurrent"""
        # blocking listeners run sequentially
        blocking = [e for e in listeners if e.blocking]
        for entry in blocking:
            try:
                if hasattr(entry.listener, 'on_event'):
                    entry.listener.on_event(event)
                elif callable(entry.listener):
                    entry.listener(event)
            except Exception as e:
                logger.error(f"Blocking listener {entry.listener} failed: {e}", exc_info=True)
        
        # async listeners - check if event loop exists
        async_listeners = [e for e in listeners if not e.blocking]
        for entry in async_listeners:
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._safe_notify(entry.listener, event))
            except RuntimeError:
                # no event loop - run synchronously
                if hasattr(entry.listener, 'on_event'):
                    entry.listener.on_event(event)
                elif callable(entry.listener):
                    entry.listener(event)
