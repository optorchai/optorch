"""Health manager for all backends"""
from typing import Dict, Any, Callable, Optional
from optorch.events.health.event_health_base import EventHealthBase
from optorch.events.health.circuit_breaker import CircuitBreaker


class EventHealthManager:
    """Manages health trackers for all backends"""
    
    def __init__(self, health_factory: Optional[Callable[[], EventHealthBase]] = None):
        self._trackers: Dict[str, EventHealthBase] = {}
        self._health_factory = health_factory or CircuitBreaker
    
    def add(self, name: str) -> EventHealthBase:
        """add health tracker for backend"""
        if name not in self._trackers:
            tracker = self._health_factory()
            self._trackers[name] = tracker
        return self._trackers[name]
    
    def remove(self, name: str) -> None:
        """remove health tracker"""
        self._trackers.pop(name, None)
    
    def get(self, name: str) -> EventHealthBase:
        """get health tracker for backend - auto-creates if missing"""
        if name not in self._trackers:
            return self.add(name)
        return self._trackers[name]
    
    def stats(self) -> Dict[str, Any]:
        """get aggregate statistics"""
        return {
            name: tracker.stats()
            for name, tracker in self._trackers.items()
        }
