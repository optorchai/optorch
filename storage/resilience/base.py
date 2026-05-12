"""Base class for resilience strategies"""
from abc import ABC, abstractmethod
from typing import Callable, TypeVar, Awaitable, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.storage.config import StorageConfig

T = TypeVar('T')


class ResilienceStrategy(ABC):
    """Abstract base for resilience strategies (retry, circuit breaker, etc.)"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier (e.g., 'retry', 'circuit_breaker')"""
        pass
    
    @classmethod
    @abstractmethod
    def from_config(cls, storage_config: "StorageConfig") -> "ResilienceStrategy":
        """
        Create strategy instance from StorageConfig.
        
        Each strategy extracts its own config from storage_config.
        Example: RetryStrategy extracts storage_config.retry
        
        Args:
            storage_config: Full storage configuration
            
        Returns:
            Configured strategy instance
        """
        pass
    
    @abstractmethod
    async def execute(self, func: Callable[[], Awaitable[T]]) -> T:
        """
        Wrap and execute async function with resilience logic.
        
        Args:
            func: Async function to protect
            
        Returns:
            Result from func()
        """
        pass
