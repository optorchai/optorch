"""Session package initialization"""
from typing import Any, Dict, Optional
from optorch.logging import get_logger
from optorch.config import ConfigManager

logger = get_logger(__name__)


class SessionPackageInitializer:
    """self-contained session initialization"""
    
    @staticmethod
    def initialize(
        config_manager: ConfigManager,
        container: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """initialize session manager from config
        
        Args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: Optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
            
        Returns:
            SessionManager instance or None
        """
        from optorch.session import SessionManager
        from optorch.session.storage import ConnectionManager, StorageConfig, RedisConfig, PostgresConfig
        from optorch.initializer_utils import extract_optorch_config
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        if overrides:
            session_dict = config_manager.merge_overrides("session", overrides, isolate=True)
            optorch_config["session"] = session_dict
        
        connection_manager = None
        storage = optorch_config.get("storage")
        if storage:
            redis_cfg = None
            postgres_cfg = None
            
            if storage.get("redis_url"):
                redis_cfg = RedisConfig(
                    url=storage["redis_url"],
                    max_connections=storage.get("redis_max_connections", 10),
                    decode_responses=storage.get("redis_decode_responses", True)
                )
            
            if storage.get("postgres_dsn"):
                postgres_cfg = PostgresConfig(
                    url=storage["postgres_dsn"],
                    min_size=storage.get("postgres_min_size", 10),
                    max_size=storage.get("postgres_max_size", 20)
                )
            
            if redis_cfg or postgres_cfg:
                connection_manager = ConnectionManager(
                    config=StorageConfig(redis=redis_cfg, postgres=postgres_cfg)
                )
        
        manager = SessionManager.from_config(optorch_config, connection_manager, config_manager=config_manager)
        
        events_config = optorch_config.get("events", {})
        if events_config:
            manager.set_event_config(events_config)
        
        if container:
            container.session_manager = manager
            logger.debug("session manager attached to container")
        
        logger.info("✅ Session management initialized")
        
        return manager
