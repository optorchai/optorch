from typing import Optional
import redis.asyncio as redis
import asyncpg
from .config import StorageConfig


class ConnectionManager:
    def __init__(self, config: StorageConfig) -> None:
        self.config = config
        self._redis: Optional[redis.Redis] = None
        self._postgres: Optional[asyncpg.Pool] = None
    
    async def redis(self) -> Optional[redis.Redis]:
        if not self.config.redis:
            return None
        
        if self._redis is None:
            self._redis = await redis.from_url(
                self.config.redis.url,
                max_connections=self.config.redis.max_connections,
                decode_responses=self.config.redis.decode_responses
            )
        
        return self._redis
    
    async def postgres(self) -> Optional[asyncpg.Pool]:
        if not self.config.postgres:
            return None
        
        if self._postgres is None:
            self._postgres = await asyncpg.create_pool(
                self.config.postgres.url,
                min_size=self.config.postgres.min_size,
                max_size=self.config.postgres.max_size
            )
        
        return self._postgres
    
    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
        if self._postgres:
            await self._postgres.close()
