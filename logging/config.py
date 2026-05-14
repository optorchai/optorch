"""Logging configuration with sensible defaults"""
from pydantic import BaseModel, Field


class LogFileConfig(BaseModel):
    """File logging configuration"""
    enabled: bool = Field(default=True, description="Enable file logging")
    path: str = Field(default="logs/optorch.log", description="Log file path")
    rotation: str = Field(
        default="daily",
        description="Rotation strategy: daily, hourly, size, or none"
    )
    retention_days: int = Field(default=30, description="Days to retain old log files")
    max_bytes: int = Field(
        default=10_000_000,
        description="Max file size in bytes before rotation (when rotation=size)"
    )
    backup_count: int = Field(default=10, description="Number of backup files to keep")


class LogConsoleConfig(BaseModel):
    """Console logging configuration"""
    enabled: bool = Field(default=True, description="Enable console logging")
    colored: bool = Field(default=True, description="Use colored output for console")


class LogsConfig(BaseModel):
    """Centralized logging configuration
    
    Provides sensible defaults. YAML overrides optional.
    Handles formatters, handlers, per-package log levels.
    """
    level: str = Field(
        default="INFO",
        description="Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    format: str = Field(
        default="%(levelname)s %(component)s %(asctime)s %(name)s %(message)s",
        description="Log message format string - %(levelname)s, %(component)s, %(asctime)s, %(name)s, %(message)s available"
    )
    date_format: str = Field(
        default="%Y-%m-%d %H:%M:%S",
        description="Timestamp format"
    )
    
    file: LogFileConfig = Field(
        default_factory=LogFileConfig,
        description="File logging settings"
    )
    console: LogConsoleConfig = Field(
        default_factory=LogConsoleConfig,
        description="Console logging settings"
    )
    
    structured: bool = Field(
        default=False,
        description="Use JSON structured logging instead of plain text"
    )
    
    package_levels: dict[str, str] = Field(
        default_factory=lambda: {
            "mcp.client.sse": "WARNING",
            "httpx": "WARNING",
            "httpcore": "WARNING",
            "asyncio": "WARNING",
            "databases": "WARNING",
            "watchfiles": "WARNING",
            "aiosqlite": "WARNING",
        },
        description="Per-package log level overrides. Defaults silence noisy libraries."
    )
