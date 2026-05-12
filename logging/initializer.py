"""Logging package initializer"""
import logging
from typing import Any, Dict, Optional
from optorch.config import ConfigManager

# use stdlib logger here - optorch logging not configured yet
logger = logging.getLogger(__name__)


class LoggingPackageInitializer:
    """self-contained logging initialization"""
    
    @staticmethod
    def initialize(
        config_manager: ConfigManager,
        container: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """initialize logging from config
        
        Args:
            config_manager: ConfigManager instance
            container: ApplicationContainer (not used for logging)
            config: Optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
        """
        from optorch.logging.config import LogsConfig
        from optorch.logging.manager import LoggingManager
        from optorch.initializer_utils import extract_optorch_config
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        if overrides:
            logging_config_dict = config_manager.merge_overrides("logging", overrides, isolate=True)
        else:
            logging_config_dict = optorch_config.get("logging", {})
        
        logs_config = LogsConfig(**logging_config_dict)

        logging_manager = LoggingManager(logs_config)
        logging_manager.setup()
        
        from optorch.logging import get_logger
        fw_logger = get_logger(__name__)
        fw_logger.info(f"✅ Logging configured {"(" + logs_config.file.path + ")" if logs_config.file.enabled else ''}", extra={
            "level": logs_config.level,
            "file_enabled": logs_config.file.enabled,
            "console_enabled": logs_config.console.enabled,
            "structured": logs_config.structured
        })
