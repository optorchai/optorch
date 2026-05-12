"""Storage configuration - Pydantic models for Redis/Postgres connections"""

from pydantic import BaseModel, Field
from typing import Optional


class RedisConfig(BaseModel):
    """Redis connection config"""
    url: str = Field(description="Redis connection URL")
    max_connections: int = Field(default=50, description="Max connections in pool")
    decode_responses: bool = Field(default=True, description="Auto-decode Redis responses")


class QdrantConfig(BaseModel):
    """Qdrant connection config"""
    url: str = Field(description="Qdrant connection URL")
    collection: str = Field(description="Qdrant collection name")


class PostgresConfig(BaseModel):
    """Postgres connection config"""
    url: str = Field(description="PostgreSQL connection URL")
    min_size: int = Field(default=10, description="Min pool size")
    max_size: int = Field(default=50, description="Max pool size")


class StorageConfig(BaseModel):
    """Session storage configuration"""
    redis: Optional[RedisConfig] = Field(default=None, description="Redis config for session backend")
    postgres: Optional[PostgresConfig] = Field(default=None, description="Postgres config for session backend")

