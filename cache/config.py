from pydantic import BaseModel, Field
from typing import Optional
from datetime import timedelta


class CacheConfig(BaseModel):
    """cache configuration"""
    backend: str = "memory"
    ttl: Optional[float] = None  # seconds
    emit_events: bool = True
    emit_on_hits: bool = False
    redis_url: Optional[str] = None
    redis_prefix: str = "cache:"
    
    @classmethod
    def from_dict(cls, data: dict) -> "CacheConfig":
        """backwards compat"""
        return cls(**data)
    
    def get_ttl_seconds(self) -> Optional[int]:
        """get ttl as integer seconds for aiocache"""
        return int(self.ttl) if self.ttl else None

