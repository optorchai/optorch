"""Authentication provider health check system"""

from typing import TYPE_CHECKING, Dict, Any, Optional
from datetime import datetime, UTC
from optorch.logging import get_logger
from optorch.identity.authentication.config import HealthCheckConfig
import asyncio

if TYPE_CHECKING:
    from optorch.identity.authentication.provider import AuthenticationProvider
    from optorch.cache.manager import CacheManager

logger = get_logger(__name__)


class ProviderHealthStatus:
    """Health status for authentication provider"""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.is_healthy = True
        self.last_check: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.consecutive_failures = 0
        self.total_checks = 0
        self.successful_checks = 0


class ProviderHealthChecker:
    """Monitors authentication provider health"""
    
    def __init__(
        self,
        providers: list["AuthenticationProvider"],
        config: Optional[HealthCheckConfig] = None,
        cache_manager: Optional["CacheManager"] = None
    ):
        self.providers = providers
        self.cache = cache_manager
        cfg = config or HealthCheckConfig()
        self.check_interval = cfg.check_interval
        self.failure_threshold = cfg.failure_threshold
        self.status: Dict[str, ProviderHealthStatus] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        for provider in providers:
            name = provider.__class__.__name__
            self.status[name] = ProviderHealthStatus(name)
    
    async def start(self) -> None:
        """Start background health checking"""
        if self._running:
            logger.debug("health checker already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        logger.info("provider health checker started")
    
    async def stop(self) -> None:
        """Stop background health checking"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("provider health checker stopped")
    
    async def _check_loop(self) -> None:
        """Background loop for health checks"""
        while self._running:
            try:
                await self.check_all()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"health check loop error: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def check_all(self) -> Dict[str, bool]:
        """Check health of all providers"""
        results = {}
        
        for provider in self.providers:
            name = provider.__class__.__name__
            is_healthy = await self._check_provider(provider, name)
            results[name] = is_healthy
        
        return results
    
    async def _check_provider(self, provider: "AuthenticationProvider", name: str) -> bool:
        """Check health of single provider"""
        status = self.status[name]
        status.total_checks += 1
        status.last_check = datetime.now(UTC)
        
        try:
            health_check = getattr(provider, 'health_check', None)
            if health_check:
                await health_check()
            else:
                if not hasattr(provider, 'authenticate'):
                    raise AttributeError("Provider missing authenticate method")
            
            status.is_healthy = True
            status.consecutive_failures = 0
            status.successful_checks += 1
            status.last_error = None
            
            logger.debug(f"provider {name} health check passed")
            return True
            
        except Exception as e:
            status.consecutive_failures += 1
            status.last_error = str(e)
            
            if status.consecutive_failures >= self.failure_threshold:
                status.is_healthy = False
                logger.error(f"provider {name} marked unhealthy after {status.consecutive_failures} failures: {e}")
            else:
                logger.warning(f"provider {name} health check failed ({status.consecutive_failures}/{self.failure_threshold}): {e}")
            
            return False
    
    def get_healthy_providers(self) -> list["AuthenticationProvider"]:
        """Get list of currently healthy providers"""
        healthy = []
        for provider in self.providers:
            name = provider.__class__.__name__
            if self.status[name].is_healthy:
                healthy.append(provider)
        return healthy
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of all provider health statuses"""
        return {
            name: {
                "healthy": status.is_healthy,
                "last_check": status.last_check.isoformat() if status.last_check else None,
                "consecutive_failures": status.consecutive_failures,
                "success_rate": (
                    status.successful_checks / status.total_checks * 100
                    if status.total_checks > 0 else 0
                ),
                "last_error": status.last_error
            }
            for name, status in self.status.items()
        }
    
    def is_provider_healthy(self, provider_name: str) -> bool:
        """Check if specific provider is healthy"""
        status = self.status.get(provider_name)
        return status.is_healthy if status else False
