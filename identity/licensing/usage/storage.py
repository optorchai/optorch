"""storage-backed usage tracker for persistent DB tracking"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime
import logging

from optorch.identity.licensing.usage.provider import UsageTrackerProvider
from optorch.identity.licensing.usage.config import StorageUsageTrackerConfig, BaseUsageTrackerConfig
from optorch.errors import ValidationError, ConfigurationError

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = logging.getLogger(__name__)


class StorageUsageTracker(UsageTrackerProvider):
    """DB-backed usage tracking via optorch storage manager
    
    production-ready persistent tracking
    supports any DB backend (postgres, mysql, sqlite)
    """
    
    def __init__(self, config: BaseUsageTrackerConfig, storage_manager: Optional["StorageManager"] = None):
        if not isinstance(config, StorageUsageTrackerConfig):
            raise ValidationError(f"Expected StorageUsageTrackerConfig, got {type(config).__name__}")
        
        self.config = config
        self.storage = storage_manager
        
        if not self.storage:
            raise ConfigurationError("storage_manager required for StorageUsageTracker")
        
    
    @property
    def name(self) -> str:
        return "storage"
    
    async def increment(
        self,
        organization_id: str,
        metric: str,
        amount: int = 1,
        window: Optional[str] = None,
    ) -> int:
        """increment counter in database with upsert"""
        if not self.storage:
            return 0
        
        window_key = self._get_window_key(window)
        
        await self.storage.query(
            "increment_usage",
            table_name=self.config.table_name,
            organization_id=organization_id,
            metric=metric,
            window=window_key,
            amount=amount,
            updated_at=datetime.now().isoformat()
        )
        
        current = await self.get_current(organization_id, metric, window)
        
        logger.debug(
            f"incremented {metric} for {organization_id} by {amount} "
            f"(window={window_key}, now={current})"
        )
        
        return current
    
    async def get_current(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> int:
        """get current count from database"""
        if not self.storage:
            return 0
        
        window_key = self._get_window_key(window)
        
        result = await self.storage.query(
            "get_usage",
            table_name=self.config.table_name,
            organization_id=organization_id,
            metric=metric,
            window=window_key
        )
        
        return result["count"] if result else 0
    
    async def reset(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> None:
        """reset counter to zero"""
        if not self.storage:
            return
        
        window_key = self._get_window_key(window)
        
        await self.storage.query(
            "reset_usage",
            table_name=self.config.table_name,
            organization_id=organization_id,
            metric=metric,
            window=window_key,
            updated_at=datetime.now().isoformat()
        )
        
        logger.debug(f"reset {metric} for {organization_id} (window={window_key})")
    
    async def get_all_metrics(self, organization_id: str) -> dict[str, int]:
        """get all metrics for an organization (lifetime counts)"""
        if not self.storage:
            return {}
        
        results = await self.storage.query(
            "get_all_usage",
            table_name=self.config.table_name,
            organization_id=organization_id,
            window="lifetime"
        )
        
        return {row["metric"]: row["count"] for row in results}
    
    def _get_window_key(self, window: Optional[str]) -> str:
        """convert window to storage key with current period"""
        if window is None:
            return "lifetime"
        
        now = datetime.now()
        
        if window == "monthly":
            return f"monthly:{now.year}-{now.month:02d}"
        elif window == "yearly":
            return f"yearly:{now.year}"
        elif window == "daily":
            return f"daily:{now.year}-{now.month:02d}-{now.day:02d}"
        else:
            # custom window
            return window
