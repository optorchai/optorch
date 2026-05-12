"""in-memory usage tracker for dev/test"""

from datetime import datetime
from typing import Optional
from collections import defaultdict
from optorch.identity.licensing.usage.provider import UsageTrackerProvider
from optorch.identity.licensing.usage.config import MemoryUsageTrackerConfig, BaseUsageTrackerConfig
from optorch.errors import ValidationError
import logging
import json

logger = logging.getLogger(__name__)


class MemoryUsageTracker(UsageTrackerProvider):
    """in-memory usage tracking using dict counters
    
    lightweight for dev/test, optional persistence to file
    NOT for production multi-instance deployments
    """
    
    def __init__(self, config: BaseUsageTrackerConfig):
        if not isinstance(config, MemoryUsageTrackerConfig):
            raise ValidationError(f"Expected MemoryUsageTrackerConfig, got {type(config).__name__}")
        
        self.config = config
        # org_id -> metric -> window -> count
        self._counters: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        
        if self.config.persist_path:
            self._load_from_disk()
    
    @property
    def name(self) -> str:
        return "memory"
    
    async def increment(
        self,
        organization_id: str,
        metric: str,
        amount: int = 1,
        window: Optional[str] = None,
    ) -> int:
        """increment counter in memory"""
        window_key = self._get_window_key(window)
        self._counters[organization_id][metric][window_key] += amount
        
        current = self._counters[organization_id][metric][window_key]
        logger.debug(
            f"incremented {metric} for {organization_id} by {amount} "
            f"(window={window_key}, now={current})"
        )
        
        if self.config.persist_path:
            self._save_to_disk()
        
        return current
    
    async def get_current(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> int:
        """get current count from memory"""
        window_key = self._get_window_key(window)
        return self._counters[organization_id][metric][window_key]
    
    async def reset(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> None:
        """reset counter to zero"""
        window_key = self._get_window_key(window)
        if organization_id in self._counters and metric in self._counters[organization_id]:
            self._counters[organization_id][metric][window_key] = 0
            logger.debug(f"reset {metric} for {organization_id} (window={window_key})")
            
            if self.config.persist_path:
                self._save_to_disk()
    
    async def get_all_metrics(self, organization_id: str) -> dict[str, int]:
        """get all metrics for an organization
        
        returns flattened dict: metric_window -> count
        e.g. {"api_calls_monthly": 100, "tool_calls_lifetime": 50}
        """
        if organization_id not in self._counters:
            return {}
        
        result = {}
        for metric, windows in self._counters[organization_id].items():
            for window_key, count in windows.items():
                window_label = window_key.split(":")[0]
                result[f"{metric}_{window_label}"] = count
        
        return result
    
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
            # custom window - use as-is
            return window
    
    def _save_to_disk(self) -> None:
        """persist counters to JSON file"""
        if not self.config.persist_path:
            return
        
        try:
            data = {}
            for org_id, metrics in self._counters.items():
                data[org_id] = {}
                for metric, windows in metrics.items():
                    data[org_id][metric] = dict(windows)
            
            with open(self.config.persist_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"persisted usage counters to {self.config.persist_path}")
        except Exception as e:
            logger.error(f"failed to persist counters: {e}")
    
    def _load_from_disk(self) -> None:
        """load counters from JSON file"""
        if not self.config.persist_path:
            return
        
        try:
            with open(self.config.persist_path, 'r') as f:
                data = json.load(f)
            
            for org_id, metrics in data.items():
                for metric, windows in metrics.items():
                    for window, count in windows.items():
                        self._counters[org_id][metric][window] = count
            
            logger.info(f"loaded usage counters from {self.config.persist_path}")
        except FileNotFoundError:
            logger.debug(f"no persisted counters found at {self.config.persist_path}")
        except Exception as e:
            logger.error(f"failed to load counters: {e}")
