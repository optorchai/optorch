from typing import TYPE_CHECKING, Dict, Any, Optional

if TYPE_CHECKING:
    from optorch.container import ApplicationContainer

from optorch.storage.config import StorageConfig
from optorch.storage.manager import StorageManager
from optorch.storage.queries.registry import QueryRegistry
from optorch.logging import get_logger
from optorch.config import ConfigManager
from optorch.container import ApplicationContainer

logger = get_logger(__name__)


class StoragePackageInitializer:
    """self-contained storage initialization"""
    
    @staticmethod
    def initialize(
        config_manager: ConfigManager,
        container: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[StorageManager]:
        """initialize storage backend from config - always lazy, migrations run on first use
        
        args:
            config_manager: ConfigManager instance
            container: application container (optional)
            config: optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
        """
        from optorch.initializer_utils import extract_optorch_config
        
        config = extract_optorch_config(config_manager, config)        
        config_manager.register_config("storage", StorageConfig)
        logger.info("✅ storage config model registered")
        
        raw_storage_config = config.get("storage")
        if not raw_storage_config:
            logger.info("storage package not configured - skipping")
            return None
        
        connection_string_key = raw_storage_config.get("connection_string")
        if connection_string_key:
            resolved = config_manager.get_secret(connection_string_key)
            if resolved:
                raw_storage_config["connection_string"] = resolved
                logger.debug(f"resolved connection_string from secret provider: {connection_string_key}")
            else:
                from optorch.errors.exceptions import ConfigurationError
                raise ConfigurationError(
                    f"storage connection_string secret not found: {connection_string_key}",
                    details={"key": connection_string_key, "secret_provider": type(config_manager.secret_provider).__name__}
                )
        
        validated = StorageConfig(**raw_storage_config)
        
        if overrides:
            for key, value in overrides.items():
                raw_storage_config[key] = value
            storage_config = StorageConfig(**raw_storage_config)
        else:
            storage_config = validated
        
        query_registry = QueryRegistry()
        logger.debug("✅ auto-discovered storage queries")
        
        manager = StorageManager(storage_config, query_registry)
        
        if container:
            container.storage_manager = manager
            logger.debug("storage manager attached to container")
            
            if hasattr(container, 'event_emitter') and container.event_emitter:
                from optorch.storage.listener import StorageListener
                
                storage_listener = StorageListener(manager)
                container.event_emitter.listeners.add(storage_listener, priority=40, tags={"storage"})
                logger.debug("storage listener registered to singleton emitter")
        
        logger.info(f"✅ storage package initialized: {storage_config.store} (lazy load)")
        
        global_auto_discover = config.get("auto_discover", True)
        package_auto_discover = storage_config.auto_discover if storage_config.auto_discover is not None else global_auto_discover
        
        if package_auto_discover and container:
            StoragePackageInitializer.discover(config_manager, container)
        elif not container:
            logger.debug("storage initialized without container - custom queries not discovered")
        else:
            logger.debug("storage auto_discover disabled - custom queries not discovered")
        
        return manager
    
    @staticmethod
    async def initialize_async(container: ApplicationContainer, entry_node: Optional[str] = None) -> None:
        """async initialization - migrations and node graph mapping
        
        args:
            container: ApplicationContainer with storage_manager
            entry_node: optional entry point for graph (reads from container if not provided)
        """
        storage_manager = getattr(container, 'storage_manager', None)
        if not storage_manager:
            logger.debug("no storage_manager - async init skipped")
            return
        
        if storage_manager.config.migrations_enabled:
            await storage_manager._ensure_initialized()
            storage_manager.disable_migrations()
            logger.info("✅ migrations complete")
        else:
            logger.debug("migrations disabled")
    
    @staticmethod
    async def run_migrations(manager: 'StorageManager') -> None:
        """run migrations immediately (call from async startup)"""
        if not manager.config.migrations_enabled:
            logger.info("migrations disabled")
            return
        
        await manager._ensure_initialized()
        logger.info("✅ migrations complete (if any)")
    
    @staticmethod
    def discover(
        config_manager: ConfigManager,
        container: Optional['ApplicationContainer'] = None,
        force: bool = False
    ) -> None:
        """discover and register custom migrations and queries
        
        args:
            config_manager: ConfigManager with storage config
            container: ApplicationContainer with storage_manager
            force: if True, ignores auto_discover flags and always discovers
        """
        from optorch.loader import AutoLoader
        
        if not container or not hasattr(container, 'storage_manager') or not container.storage_manager:
            logger.warning("no storage_manager - custom migrations/queries not discovered")
            return
        
        storage_config = container.storage_manager.config
        
        optorch_config = config_manager.get("optorch", {})
        global_auto_discover = optorch_config.get("auto_discover", True)
        
        if "auto_discover" in storage_config.model_fields_set:
            package_auto_discover = storage_config.auto_discover
        else:
            package_auto_discover = global_auto_discover
        
        if not force and not package_auto_discover:
            logger.debug("storage auto_discover disabled (global or package level)")
            return
        
        if force or (package_auto_discover and storage_config.custom_queries.auto_discover):
            queries_config = config_manager.get("custom_queries")
            if queries_config:
                query_registry = container.storage_manager.query_registry
                ok, fail = AutoLoader.register(
                    query_registry,
                    queries_config,
                    storage_config.custom_queries.module,
                    instantiate=storage_config.custom_queries.instantiate
                )
                logger.info(f"✅ discovered {ok} custom queries from {storage_config.custom_queries.module} ({fail} failed)")
            else:
                logger.debug("no custom_queries config - custom queries not discovered")
