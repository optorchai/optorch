"""pydantic configs for usage trackers"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


class BaseUsageTrackerConfig(BaseModel):
    """base configuration for all usage trackers"""
    pass


class MemoryUsageTrackerConfig(BaseUsageTrackerConfig):
    """config for in-memory usage tracker (dev/test)"""
    persist_path: Optional[str] = Field(
        default=None,
        description="optional path to persist counters on shutdown"
    )


class RedisUsageTrackerConfig(BaseUsageTrackerConfig):
    """config for Redis usage tracker (production)"""
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    key_prefix: str = Field(default="usage:", description="Key prefix for all counters")
    ttl_seconds: Optional[int] = Field(
        default=None,
        description="TTL for counter keys (None = no expiry)"
    )


class StorageUsageTrackerConfig(BaseUsageTrackerConfig):
    """config for storage-backed usage tracker (DB-agnostic)"""
    table_name: str = Field(
        default="usage_metrics",
        description="Table name for usage data"
    )
    create_table: bool = Field(
        default=True,
        description="Auto-create table if not exists"
    )


class UsageTrackerConfig(BaseModel):
    """unified usage tracker configuration"""
    type: Literal["memory", "redis", "storage", "custom"] = Field(
        default="memory",
        description="Usage tracker backend type"
    )
    enabled: bool = Field(default=True, description="Enable usage tracking")
    
    memory: Optional[MemoryUsageTrackerConfig] = None
    redis: Optional[RedisUsageTrackerConfig] = None
    storage: Optional[StorageUsageTrackerConfig] = None
    
    custom_class: Optional[str] = Field(
        default=None,
        description="Custom tracker class path"
    )
    custom_config: Optional[dict] = Field(
        default=None,
        description="Custom tracker config"
    )
