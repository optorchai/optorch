"""cache package initializer"""

from optorch.logging import get_logger
from typing import Dict, Any, Optional
from optorch.config import ConfigManager

logger = get_logger(__name__)


class CachePackageInitializer:
    """self-contained cache initialization"""
    
    @staticmethod
    def initialize(
        config_manager: ConfigManager,
        container: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """initialize cache manager from config
        
        args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
            
        returns:
            CacheManager instance or None
        """
        from optorch.cache.manager import CacheManager
        from optorch.cache.config import CacheConfig
        from optorch.initializer_utils import extract_optorch_config
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        config_manager.register_config("cache", CacheConfig)
        logger.debug("✅ cache config model registered")
        
        if overrides:
            cache_dict = config_manager.merge_overrides("cache", overrides, isolate=True)
        else:
            cache_dict = optorch_config.get("cache", {})
        
        cache_config = CacheConfig(**cache_dict) if cache_dict else CacheConfig()
        manager = CacheManager(config=cache_config)
        
        if container:
            container.cache_manager = manager
        
        logger.info(f"✅ CacheManager initialized ({cache_config.backend} backend)")
        
        return manager
