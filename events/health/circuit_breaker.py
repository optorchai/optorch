"""Circuit breaker health tracker"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from optorch.events.health.event_health_base import EventHealthBase


class CircuitBreaker(EventHealthBase):
    """Tracks backend health with circuit breaker pattern"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: timedelta = timedelta(seconds=60)
    ):
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._failures = 0
        self._successes = 0
        self._last_failure: Optional[datetime] = None
        self._open_until: Optional[datetime] = None
    
    def is_healthy(self) -> bool:
        """check circuit state"""
        # circuit open, check if timeout passed
        if self._open_until and datetime.now() < self._open_until:
            return False
        
        # reset if timeout passed
        if self._open_until and datetime.now() >= self._open_until:
            self._failures = 0
            self._open_until = None
        
        return True
    
    def success(self) -> None:
        """record success"""
        self._successes += 1
        # decay failures on success
        if self._failures > 0:
            self._failures = max(0, self._failures - 1)
    
    def error(self, exception: Exception) -> None:
        """record error and potentially open circuit"""
        self._failures += 1
        self._last_failure = datetime.now()
        
        if self._failures >= self._failure_threshold:
            self._open_until = datetime.now() + self._reset_timeout
    
    def stats(self) -> Dict[str, Any]:
        """get statistics"""
        return {
            "healthy": self.is_healthy(),
            "failures": self._failures,
            "successes": self._successes,
            "last_failure": self._last_failure.isoformat() if self._last_failure else None,
            "open_until": self._open_until.isoformat() if self._open_until else None
        }
