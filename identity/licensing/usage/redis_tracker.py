"""redis-backed usage tracker for distributed deployments"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime
import logging

from optorch.identity.licensing.usage.provider import UsageTrackerProvider
from optorch.identity.licensing.usage.config import RedisUsageTrackerConfig, BaseUsageTrackerConfig
from optorch.errors import ValidationError, ConfigurationError

if TYPE_CHECKING:
    import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisUsageTracker(UsageTrackerProvider):
    """redis usage tracking using INCR/HINCRBY
    
    production-ready for distributed deployments
    automatic TTL handling for time windows
    """
    
    def __init__(self, config: BaseUsageTrackerConfig):
        if not isinstance(config, RedisUsageTrackerConfig):
            raise ValidationError(f"Expected RedisUsageTrackerConfig, got {type(config).__name__}")
        
        self.config = config
        
        try:
            import redis.asyncio as redis
        except ImportError:
            raise ConfigurationError("redis package required for RedisUsageTracker (pip install redis)")
        
        # redis.asyncio typing is incomplete - methods ARE coroutines despite stubs
        self._redis = redis.Redis(  # type: ignore[call-arg]
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            password=self.config.password,
            decode_responses=True,
        )
    
    @property
    def name(self) -> str:
        return "redis"
    
    async def increment(
        self,
        organization_id: str,
        metric: str,
        amount: int = 1,
        window: Optional[str] = None,
    ) -> int:
        """increment counter in redis with TTL"""
        key = self._make_key(organization_id, metric, window)
        
        # increment counter
        new_value = await self._redis.hincrby(key, "count", amount)  # type: ignore[misc]
        
        # set TTL if window-based and not already set
        if window and self.config.ttl_seconds:
            ttl = await self._redis.ttl(key)  # type: ignore[misc]
            if ttl == -1:  # no expiration set
                await self._redis.expire(key, self.config.ttl_seconds)  # type: ignore[misc]
        
        logger.debug(
            f"incremented {metric} for {organization_id} by {amount} "
            f"(window={window}, now={new_value})"
        )
        
        return int(new_value)
    
    async def get_current(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> int:
        """get current count from redis"""
        key = self._make_key(organization_id, metric, window)
        value = await self._redis.hget(key, "count")  # type: ignore[misc]
        return int(value) if value else 0
    
    async def reset(
        self,
        organization_id: str,
        metric: str,
        window: Optional[str] = None,
    ) -> None:
        """reset counter to zero"""
        key = self._make_key(organization_id, metric, window)
        await self._redis.hset(key, "count", "0")  # type: ignore[misc]
        logger.debug(f"reset {metric} for {organization_id} (window={window})")
    
    async def get_all_metrics(self, organization_id: str) -> dict[str, int]:
        """get all metrics for an organization (lifetime counts)"""
        pattern = self._make_key(organization_id, "*", None)
        keys = await self._redis.keys(pattern)  # type: ignore[misc]
        
        result = {}
        for key in keys:
            # extract metric name from key
            # key format: prefix:org_id:metric:window
            parts = key.split(":")
            if len(parts) >= 3:
                metric = parts[2]
                value = await self._redis.hget(key, "count")  # type: ignore[misc]
                if value:
                    result[metric] = int(value)
        
        return result
    
    def _make_key(self, organization_id: str, metric: str, window: Optional[str]) -> str:
        """construct redis key with window period"""
        window_suffix = self._get_window_suffix(window)
        return f"{self.config.key_prefix}:{organization_id}:{metric}:{window_suffix}"
    
    def _get_window_suffix(self, window: Optional[str]) -> str:
        """convert window to key suffix with current period"""
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
    
    async def close(self) -> None:
        """cleanup redis connection"""
        await self._redis.aclose()
