"""usage tracker registry"""

from typing import Type, Optional
from optorch.registry import Registry
from optorch.identity.licensing.usage.provider import UsageTrackerProvider
from optorch.identity.licensing.usage.config import UsageTrackerConfig, BaseUsageTrackerConfig
import logging

logger = logging.getLogger(__name__)


class UsageTrackerRegistry:
    """registry for usage tracker providers
    
    follows optorch registry pattern - instance-based, no singletons
    """
    
    def __init__(self):
        self._providers = Registry[Type[UsageTrackerProvider]]()
        self._register_builtins()
    
    def _register_builtins(self):
        """register built-in usage tracker backends"""
        from optorch.identity.licensing.usage.memory import MemoryUsageTracker
        
        self.register("memory", MemoryUsageTracker)
        logger.debug("registered builtin usage tracker: memory")
        
        try:
            from optorch.identity.licensing.usage.redis_tracker import RedisUsageTracker
            self.register("redis", RedisUsageTracker)
            logger.debug("registered builtin usage tracker: redis")
        except ImportError:
            logger.debug("redis usage tracker not available (missing redis dependency)")
        
        try:
            from optorch.identity.licensing.usage.storage import StorageUsageTracker
            self.register("storage", StorageUsageTracker)
            logger.debug("registered builtin usage tracker: storage")
        except ImportError:
            logger.debug("storage usage tracker not available")
    
    def register(self, name: str, provider_class: Type[UsageTrackerProvider]) -> None:
        """register usage tracker provider class"""
        self._providers.register(name, provider_class)
        logger.debug(f"registered usage tracker: {name}")
    
    def has(self, name: str) -> bool:
        """check if tracker type registered"""
        return self._providers.has(name)
    
    def get(self, name: str) -> Type[UsageTrackerProvider]:
        """get tracker provider class by name"""
        return self._providers.get(name)
    
    def list_providers(self) -> list[str]:
        """list registered tracker types"""
        return self._providers.list_keys()
    
    async def create(
        self,
        config: UsageTrackerConfig,
        **kwargs
    ) -> Optional[UsageTrackerProvider]:
        """create usage tracker instance from config
        
        Args:
            config: UsageTrackerConfig with type and backend-specific config
            **kwargs: Additional dependencies (storage_manager, cache_manager, etc)
        
        Returns:
            UsageTrackerProvider instance or None if disabled
        """
        if not config.enabled:
            logger.debug("usage tracking disabled")
            return None
        
        if config.type == "custom" and config.custom_class:
            return await self._create_custom(config, **kwargs)
        
        if not self._providers.has(config.type):
            logger.warning(f"unknown usage tracker type: {config.type}")
            return None
        
        provider_class = self._providers.get(config.type)
        
        type_config: Optional[BaseUsageTrackerConfig] = None
        if config.type == "memory" and config.memory:
            type_config = config.memory
        elif config.type == "redis" and config.redis:
            type_config = config.redis
        elif config.type == "storage" and config.storage:
            type_config = config.storage
        
        if type_config is None:
            logger.warning(f"missing config for usage tracker type: {config.type}")
            return None
        
        if config.type == "memory":
            return provider_class(type_config)  # type: ignore[call-arg]
        else:
            return provider_class(type_config, **kwargs)  # type: ignore[call-arg]
    
    async def _create_custom(
        self,
        config: UsageTrackerConfig,
        **kwargs
    ) -> Optional[UsageTrackerProvider]:
        """create custom usage tracker from class path"""
        if not config.custom_class:
            logger.error("custom usage tracker requires custom_class")
            return None
        
        try:
            module_path, class_name = config.custom_class.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            custom_class = getattr(module, class_name)
            return custom_class(config.custom_config or {}, **kwargs)
        except Exception as e:
            logger.error(f"failed to create custom usage tracker: {e}")
            return None
