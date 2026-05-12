"""Session package configuration"""
from pydantic import BaseModel, Field
from typing import Dict, Any


class SessionConfig(BaseModel):
    """session backend configuration"""
    
    backend: str = Field(
        default="memory",
        description="session storage backend (memory, redis, postgres, or custom)"
    )
    ttl: int = Field(
        default=86400,
        description="session TTL in seconds - 0 = no expiry"
    )
    memory: Dict[str, Any] = Field(
        default={},
        description="memory backend params"
    )
    redis: Dict[str, Any] = Field(
        default={"host": "localhost", "port": 6379, "db": 0},
        description="redis connection params"
    )
