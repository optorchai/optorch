"""Base class for pool load balancing strategies"""
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.llm.base_client import BaseLLMClient

class LoadBalancingStrategy(ABC):
    """Base class for pool load balancing strategies"""
    
    @property
    def name(self) -> str:
        """Strategy name for registration"""
        return self.__class__.__name__.replace("Strategy", "").lower()
    
    @abstractmethod
    async def select_client(self, clients: List['BaseLLMClient'], request_size: int) -> 'BaseLLMClient':
        """
        Select a client from the pool for the next request.
        
        Args:
            clients: Available clients in the pool
            request_size: Estimated token count for request
        
        Returns:
            Selected client
        """
        pass
