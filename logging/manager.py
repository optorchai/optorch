"""Logging setup and configuration manager"""
import logging
import sys
from pathlib import Path
from typing import Optional

from optorch.logging.config import LogsConfig
from optorch.logging.context_formatter import ContextFormatter
from optorch.logging.json_formatter import JSONFormatter


class LoggingManager:
    """Manages logging configuration and provides access to log file paths"""
    
    def __init__(self, config: Optional[LogsConfig] = None):
        self.config = config or LogsConfig()
        self._initialized = False
    
    def setup(self) -> None:
        """Configure Python logging based on stored config"""
        if self._initialized:
            return
        
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.level.upper()))
        root_logger.handlers.clear()
        
        if self.config.structured:
            formatter = JSONFormatter()
        else:
            formatter = ContextFormatter(fmt=self.config.format, datefmt=self.config.date_format, use_color=True)
            file_formatter = ContextFormatter(fmt=self.config.format, datefmt=self.config.date_format, use_color=False)
        
        if self.config.console.enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        if self.config.file.enabled:
            log_path = Path(self.config.file.path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(str(log_path))
            file_handler.setFormatter(file_formatter if not self.config.structured else formatter)
            root_logger.addHandler(file_handler)
        
        for package, level in self.config.package_levels.items():
            logging.getLogger(package).setLevel(getattr(logging, level.upper()))
        
        self._initialized = True
    
    def get_log_file_path(self) -> Optional[Path]:
        """Get configured log file path
        
        Returns None if file logging is disabled.
        """
        if not self.config.file.enabled:
            return None
        
        return Path(self.config.file.path)
