from pydantic import BaseModel, Field
from typing import Optional, TYPE_CHECKING
from optorch.config.path_config import PathConfig
from optorch.storage.types import StorageRole

if TYPE_CHECKING:
    from optorch.storage.tenant_filter import TenantFilterConfig


class RetryConfig(BaseModel):
    """Retry configuration with exponential backoff"""
    enabled: bool = Field(default=True, description="Enable retry logic")
    max_retries: int = Field(default=3, ge=1, description="Maximum retry attempts")
    initial_delay: float = Field(default=1.0, gt=0, description="Initial delay in seconds")
    max_delay: float = Field(default=30.0, gt=0, description="Maximum delay between retries")
    exponential_base: float = Field(default=2.0, gt=1, description="Multiplier for exponential backoff")


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration"""
    enabled: bool = Field(default=True, description="Enable circuit breaker pattern")
    failure_threshold: int = Field(default=5, ge=1, description="Consecutive failures before opening")
    recovery_timeout: float = Field(default=60.0, gt=0, description="Seconds before trying HALF_OPEN")
    success_threshold: int = Field(default=2, ge=1, description="Successes in HALF_OPEN before CLOSED")


class StorageConfig(BaseModel):
    """storage backend configuration"""
    
    auto_discover: bool | None = Field(default=None, description="enable custom queries discovery")
    custom_queries: PathConfig = Field(
        default_factory=lambda: PathConfig(module="app.storage.queries", auto_discover=True, instantiate=False),
        description="custom queries discovery config"
    )
    
    store: str = Field(
        default="timescale",
        description="storage backend type: timescale, sqlite, mysql"
    )
    connection_string: str = Field(
        default="sqlite:///data/optorch.db",
        description="database connection string (supports env vars or literal value)"
    )
    pool_size: int = Field(
        default=5,
        description="connection pool size"
    )
    pool_timeout: int = Field(
        default=30,
        description="connection pool timeout in seconds"
    )
    migrations_enabled: bool = Field(
        default=True,
        description="enable automatic migrations on startup"
    )
    migrations_path: Optional[str] = Field(
        default=None,
        description="path to migrations directory (defaults to optorch/storage/migrations/) - expects subdir of store type"
    )
    
    role: StorageRole = Field(
        default=StorageRole.WRITE,
        description="Storage access role: READ (analytics), WRITE (orchestrator), or READ_WRITE (both)"
    )
    
    retry: RetryConfig = Field(default_factory=RetryConfig, description="Retry configuration")
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig, description="Circuit breaker configuration")
    resilience_strategies: list[str] = Field(
        default=["retry", "circuit_breaker"],
        description="Ordered list of resilience strategies to apply (executed in order)"
    )
    
    tenant_filter: Optional["TenantFilterConfig"] = Field(
        default=None,
        description="Multi-tenancy filtering config - automatic organization_id injection"
    )
    
    class Config:
        arbitrary_types_allowed = True


# avoid circular import - rebuild after TenantFilterConfig defined
def _rebuild_storage_config():
    from optorch.storage.tenant_filter import TenantFilterConfig
    StorageConfig.model_rebuild()
