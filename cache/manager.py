from typing import Optional, Any, Protocol, cast, TYPE_CHECKING
from aiocache import caches
from aiocache.serializers import JsonSerializer
from .config import CacheConfig

if TYPE_CHECKING:
    from optorch.controller.node_context import NodeContext


class CacheBackend(Protocol):
    """Protocol for cache backend"""
    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def clear(self) -> None: ...
    async def exists(self, key: str) -> bool: ...


class CacheManager:
    def __init__(self, config: CacheConfig) -> None:
        self.config = config
        self._register_backend()
        self.backend: CacheBackend = cast(CacheBackend, caches.get('default'))
    
    def _register_backend(self) -> None:
        cache_config = {
            'default': {
                'cache': f"aiocache.{self._get_cache_class()}",
                'serializer': {
                    'class': "aiocache.serializers.JsonSerializer"
                }
            }
        }
        
        ttl_seconds = self.config.get_ttl_seconds()
        if ttl_seconds:
            cache_config['default']['ttl'] = ttl_seconds
        
        if self.config.backend == "redis":
            cache_config['default']['endpoint'] = self.config.redis_url or "127.0.0.1"
            cache_config['default']['port'] = 6379
            cache_config['default']['namespace'] = self.config.redis_prefix
        
        caches.set_config(cache_config)
    
    def _get_cache_class(self) -> str:
        if self.config.backend == "memory":
            return "SimpleMemoryCache"
        elif self.config.backend == "redis":
            return "RedisCache"
        else:
            raise ValueError(f"Unknown cache backend: {self.config.backend}")
    
    async def get(self, key: str, context: Optional['NodeContext'] = None) -> Any:
        value = await self.backend.get(key)
        
        if context and context.events and self.config.emit_events:
            if value is None:
                context.events.emit("cache.miss", {"key": key})
            elif self.config.emit_on_hits:
                context.events.emit("cache.hit", {"key": key})
        
        return value
    
    async def set(self, key: str, value: Any, ttl: Any = None, context: Optional['NodeContext'] = None) -> None:
        ttl_seconds = None
        if ttl:
            ttl_seconds = int(ttl.total_seconds()) if hasattr(ttl, 'total_seconds') else ttl
        else:
            ttl_seconds = self.config.get_ttl_seconds()
            
        await self.backend.set(key, value, ttl=ttl_seconds)
        
        if context and context.events and self.config.emit_events:
            context.events.emit("cache.set", {"key": key})
            
    async def delete(self, key: str) -> None:
        await self.backend.delete(key)
    
    async def clear(self) -> None:
        await self.backend.clear()
    
    async def exists(self, key: str) -> bool:
        return await self.backend.exists(key)
