"""Circuit breaker strategy"""
import time
from enum import Enum
from typing import Callable, TypeVar, Awaitable, Optional, TYPE_CHECKING
from optorch.storage.resilience.base import ResilienceStrategy
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.config import StorageConfig, CircuitBreakerConfig

logger = get_logger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is OPEN"""
    pass


class CircuitBreakerStrategy(ResilienceStrategy):
    """Circuit breaker resilience strategy"""
    
    def __init__(self, config: "CircuitBreakerConfig"):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
    
    @property
    def name(self) -> str:
        return "circuit_breaker"
    
    @classmethod
    def from_config(cls, storage_config: "StorageConfig") -> "CircuitBreakerStrategy":
        """Extract circuit breaker config from storage config"""
        return cls(storage_config.circuit_breaker)
    
    async def execute(self, func: Callable[[], Awaitable[T]]) -> T:
        """Execute with circuit breaker protection"""
        if not self.config.enabled:
            return await func()
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("circuit_breaker_half_open")
            else:
                logger.warning("circuit_breaker_rejecting: state=open")
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        try:
            result = await func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to try HALF_OPEN"""
        if self.last_failure_time is None:
            return False
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("circuit_breaker_closed")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("circuit_breaker_opened_from_half_open")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"circuit_breaker_opened: failures={self.failure_count}")
