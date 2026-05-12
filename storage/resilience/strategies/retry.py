"""Retry strategy with exponential backoff"""
import asyncio
from typing import Callable, TypeVar, Awaitable, TYPE_CHECKING
from optorch.storage.resilience.base import ResilienceStrategy
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.config import StorageConfig, RetryConfig

logger = get_logger(__name__)

T = TypeVar('T')


class RetryStrategy(ResilienceStrategy):
    """Retry with exponential backoff resilience strategy"""
    
    def __init__(self, config: "RetryConfig"):
        self.config = config
    
    @property
    def name(self) -> str:
        return "retry"
    
    @classmethod
    def from_config(cls, storage_config: "StorageConfig") -> "RetryStrategy":
        """Extract retry config from storage config"""
        return cls(storage_config.retry)
    
    async def execute(self, func: Callable[[], Awaitable[T]]) -> T:
        """Retry async function with exponential backoff"""
        if not self.config.enabled:
            return await func()
        
        delay = self.config.initial_delay
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                
                if attempt == self.config.max_retries:
                    logger.error(
                        f"max_retries_exceeded: max_retries={self.config.max_retries}, error={e}"
                    )
                    raise
                
                logger.warning(
                    f"retry_attempt: attempt={attempt + 1}/{self.config.max_retries}, "
                    f"delay={delay}s, error={e}"
                )
                
                await asyncio.sleep(delay)
                delay = min(delay * self.config.exponential_base, self.config.max_delay)
        
        if last_exception:
            raise last_exception
        raise RuntimeError("Unreachable code")
