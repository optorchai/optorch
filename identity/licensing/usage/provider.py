"""usage tracker provider ABC"""

from abc import ABC, abstractmethod
from typing import Optional


class UsageTrackerProvider(ABC):
    """abstract base for usage tracking backends
    
    follows optorch registry pattern - backend agnostic
    """
    
    @abstractmethod
    async def increment(
        self,
        organization_id: str,
        metric: str,
        amount: int = 1,
        window: Optional[str] = None,
    ) -> int:
        """increment usage counter
        
        Args:
            organization_id: Tenant/org identifier
            metric: What to track (workflow_executions, api_calls, storage_gb, etc)
            amount: How much to increment by (default 1)
            window: Time window (monthly, yearly, None for lifetime)
        
        Returns:
            Current count after increment
        """
        pass
    
    @abstractmethod
    async def get_current(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> int:
        """get current usage count
        
        Args:
            organization_id: Tenant/org identifier
            metric: What to query
            window: Time window (monthly, yearly, None for lifetime)
        
        Returns:
            Current count
        """
        pass
    
    @abstractmethod
    async def reset(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> None:
        """reset usage counter
        
        Args:
            organization_id: Tenant/org identifier
            metric: What to reset
            window: Time window to reset
        """
        pass
    
    @abstractmethod
    async def get_all_metrics(self, organization_id: str) -> dict[str, int]:
        """get all metrics for an organization
        
        Args:
            organization_id: Tenant/org identifier
        
        Returns:
            Dict of metric -> current_count
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """provider name for logging"""
        pass
