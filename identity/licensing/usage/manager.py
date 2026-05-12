"""usage tracking manager facade"""

from typing import Optional
from optorch.identity.licensing.usage.provider import UsageTrackerProvider
from optorch.identity.licensing.usage.registry import UsageTrackerRegistry
from optorch.identity.licensing.usage.config import UsageTrackerConfig
import logging

logger = logging.getLogger(__name__)


class UsageManager:
    """high-level usage tracking coordinator
    
    facade over usage tracker backends
    integrates with license manager for enforcement
    """
    
    def __init__(
        self,
        config: UsageTrackerConfig,
        registry: Optional[UsageTrackerRegistry] = None,
        **dependencies
    ):
        self.config = config
        self.registry = registry or UsageTrackerRegistry()
        self.dependencies = dependencies
        self.tracker: Optional[UsageTrackerProvider] = None
    
    async def initialize(self) -> None:
        """create tracker instance from config"""
        self.tracker = await self.registry.create(self.config, **self.dependencies)
        
        if self.tracker:
            logger.info(f"initialized usage tracker: {self.tracker.name}")
        else:
            logger.debug("usage tracking disabled")
    
    async def track(
        self,
        organization_id: str,
        metric: str,
        amount: int = 1,
        window: Optional[str] = None,
    ) -> int:
        """track usage metric (convenience wrapper for increment)
        
        Args:
            organization_id: Tenant/org identifier
            metric: What to track (workflow_executions, api_calls, etc)
            amount: How much to increment by
            window: Time window (monthly, yearly, None for lifetime)
        
        Returns:
            Current count after increment
        """
        if not self.tracker:
            logger.debug("usage tracking disabled, skipping track")
            return 0
        
        return await self.tracker.increment(organization_id, metric, amount, window)
    
    async def get_usage(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> int:
        """get current usage for a metric
        
        Args:
            organization_id: Tenant/org identifier
            metric: What to query
            window: Time window (monthly, yearly, None for lifetime)
        
        Returns:
            Current usage count
        """
        if not self.tracker:
            return 0
        
        return await self.tracker.get_current(organization_id, metric, window)
    
    async def reset_usage(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> None:
        """reset usage counter to zero
        
        Args:
            organization_id: Tenant/org identifier
            metric: What to reset
            window: Time window (monthly, yearly, None for lifetime)
        """
        if not self.tracker:
            logger.debug("usage tracking disabled, skipping reset")
            return
        
        await self.tracker.reset(organization_id, metric, window)
    
    async def get_all_usage(self, organization_id: str) -> dict[str, int]:
        """get all usage metrics for an organization
        
        Args:
            organization_id: Tenant/org identifier
        
        Returns:
            Dict mapping metric names to lifetime counts
        """
        if not self.tracker:
            return {}
        
        return await self.tracker.get_all_metrics(organization_id)
    
    @property
    def enabled(self) -> bool:
        """check if usage tracking is enabled"""
        return self.config.enabled and self.tracker is not None
    
    @property
    def backend_name(self) -> Optional[str]:
        """get active backend name"""
        return self.tracker.name if self.tracker else None
