"""Backend manager for event distribution"""
from typing import Dict, Any, Optional
from optorch.logging import get_logger
from optorch.events.listener_manager import ListenerManager
from optorch.events.backend import EventBackend
from optorch.events.distribution.distribution_strategy import DistributionStrategy
from optorch.events.distribution.tag_based_strategy import TagBasedStrategy
from optorch.events.health.event_health_manager import EventHealthManager

logger = get_logger(__name__)


class BackendManager:
    """Distributes events to backends via strategy"""
    
    def __init__(
        self,
        listener_manager: ListenerManager,
        strategy: Optional[DistributionStrategy] = None
    ):
        self._listener_manager = listener_manager
        self._backends: Dict[str, EventBackend] = {}
        self._strategy = strategy or TagBasedStrategy()
        self._health = EventHealthManager()
    
    @property
    def listeners(self) -> ListenerManager:
        """expose listener manager for registration"""
        return self._listener_manager
    
    @property
    def health(self) -> EventHealthManager:
        """expose health manager"""
        return self._health
    
    def add(self, name: str, backend: EventBackend) -> None:
        """add backend with auto health tracking"""
        self._backends[name] = backend
        self._health.add(name)
        logger.info(f"Registered backend: {name}")
    
    def remove(self, name: str) -> None:
        """remove backend"""
        self._backends.pop(name, None)
        self._health.remove(name)
    
    def get(self, name: str) -> Optional[EventBackend]:
        """get backend by name"""
        return self._backends.get(name)
    
    def notify(self, event_type: str, event: Dict[str, Any]) -> None:
        """distribute event to all healthy backends"""
        all_listeners = self._listener_manager.for_event(event)
        
        if not all_listeners:
            return
        
        for name, backend in self._backends.items():
            health = self._health.get(name)
            
            if not health.is_healthy():
                logger.warning(f"Backend {name} unhealthy - skipping")
                continue
            
            try:
                # per-backend distribution
                listeners = self._strategy.distribute(all_listeners, backend)
                
                if listeners:
                    backend.notify(listeners, event_type, event)
                    health.success()
                    
            except Exception as e:
                logger.error(f"Backend {name} failed: {e}", exc_info=True)
                health.error(e)
    
    async def close_all(self) -> None:
        """close all backends - cleanup connections"""
        for name, backend in self._backends.items():
            try:
                await backend.close()
                logger.info(f"Backend {name} closed")
            except Exception as e:
                logger.error(f"Failed to close backend {name}: {e}")
