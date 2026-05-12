"""Configuration models for authentication components"""

from pydantic import BaseModel, Field
from typing import Optional


class HealthCheckConfig(BaseModel):
    """Configuration for provider health checking"""
    
    check_interval: int = Field(default=60, description="seconds between health checks")
    failure_threshold: int = Field(default=3, description="consecutive failures before marking unhealthy")


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting"""
    
    max_attempts: int = Field(default=5, description="max failed attempts in window")
    window_seconds: int = Field(default=300, description="time window in seconds")
    lockout_seconds: int = Field(default=900, description="lockout duration after exceeding limit")
    identify_by: str = Field(default="email", description="identify by: email, ip, or both")


class RetryConfig(BaseModel):
    """Configuration for retry fallback strategy"""
    
    max_attempts: int = Field(default=2, description="max retry attempts")
    base_delay: float = Field(default=0.1, description="base delay for exponential backoff")


class CacheConfig(BaseModel):
    """Configuration for cached auth fallback strategy"""
    
    ttl_seconds: int = Field(default=300, description="cache TTL in seconds")


class FallbackConfig(BaseModel):
    """Configuration for fallback handling"""
    
    retry: Optional[RetryConfig] = Field(default_factory=RetryConfig)
    cache: Optional[CacheConfig] = None
    enable_retry: bool = Field(default=True, description="enable retry strategy")
    enable_cache: bool = Field(default=False, description="enable cache strategy")


class KeyRotationConfig(BaseModel):
    """Configuration for JWT key rotation"""
    
    enable_auto_rotation: bool = Field(default=True, description="enable automatic key rotation")
    rotation_days: int = Field(default=90, ge=1, le=365, description="rotate keys every N days")
    grace_period_days: int = Field(default=7, ge=1, le=30, description="keep old keys valid for N days after rotation")
    check_interval_hours: int = Field(default=24, ge=1, le=168, description="check for rotation every N hours")
