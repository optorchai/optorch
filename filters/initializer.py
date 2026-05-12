"""filters package initializer"""
from optorch.logging import get_logger
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from optorch.config import ConfigManager
    from optorch.container import ApplicationContainer

logger = get_logger(__name__)


class FiltersPackageInitializer:
    """initializes filter domain/target mappings"""
    
    @staticmethod
    def initialize(
        config_manager: 'ConfigManager',
        container: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """initialize filter domain/target mappings from config
        
        args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
            
        returns:
            None (filters registered globally in FilterRegistry)
        """
        from optorch.filters.filter_registry import FilterRegistry
        from optorch.filters.config import FilterConfig
        from optorch.initializer_utils import extract_optorch_config
        from optorch.loader import AutoLoader
        
        if FilterRegistry._domain_targets:
            logger.debug("Filters already initialized")
            return
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        config_manager.register_config("optorch.filters", FilterConfig)
        logger.info("✅ filters config model registered")
        
        AutoLoader.import_packages(["optorch.filters"])
        logger.debug("✅ Built-in filters imported and registered")
        
        if overrides:
            filters_dict = config_manager.merge_overrides("optorch.filters", overrides, isolate=True)
        else:
            filters_dict = optorch_config.get("filters", {})
        
        filters_config = FilterConfig(**filters_dict) if filters_dict else FilterConfig()
        domains = filters_config.domains
        
        for domain, targets in domains.items():
            for target, filter_names in targets.items():
                FilterRegistry.register_target(domain, target, filter_names)
                logger.debug(f"Registered filters for {domain}.{target}")
        
        logger.info(f"✅ Filters initialized: {len(domains)} domains")

        global_auto_discover = optorch_config.get("auto_discover", True)
        package_auto_discover = filters_config.auto_discover if filters_config.auto_discover is not None else global_auto_discover
        
        if package_auto_discover:
            FiltersPackageInitializer.discover(config_manager, container)
        else:
            logger.debug("filters auto_discover disabled - custom filters not discovered")
    
    @staticmethod
    def discover(
        config_manager: 'ConfigManager',
        container: Optional['ApplicationContainer'] = None,
        force: bool = False
    ) -> None:
        """discover and register custom filters from config
        
        args:
            config_manager: ConfigManager with filters config
            container: ApplicationContainer (optional)
            force: if True, ignores auto_discover flags and always discovers
        """
        from optorch.filters.config import FilterConfig
        from optorch.filters.filter_registry import FilterRegistry
        from optorch.loader import AutoLoader
        
        optorch_config = config_manager.get("optorch", {})
        global_auto_discover = optorch_config.get("auto_discover", True)
        
        filters_config_model = config_manager._get_typed_config("optorch.filters") if "optorch.filters" in config_manager._models else None
        filters_config: FilterConfig | None = filters_config_model if isinstance(filters_config_model, FilterConfig) else None
        
        if filters_config is None:
            logger.debug("no filters config - discovery skipped")
            return
        
        if "auto_discover" in filters_config.model_fields_set:
            package_auto_discover = filters_config.auto_discover
        else:
            package_auto_discover = global_auto_discover
        
        if not force and not package_auto_discover:
            logger.debug("filters auto_discover disabled (global or package level)")
            return
        
        if force or (package_auto_discover and filters_config.filters_path.auto_discover):
            filters_config_dict = config_manager.get("custom_filters")
            if filters_config_dict:
                ok, fail = AutoLoader.register(
                    FilterRegistry,
                    filters_config_dict,
                    filters_config.filters_path.module,
                    instantiate=filters_config.filters_path.instantiate
                )
                logger.info(f"✅ discovered {ok} custom filters from {filters_config.filters_path.module} ({fail} failed)")
            else:
                logger.debug("no custom_filters config - custom filters not discovered")
