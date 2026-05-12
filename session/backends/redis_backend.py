import json
from typing import Dict, Any, Optional
from contextvars import ContextVar
from optorch.session.backends.base_backend import SessionBackend

_current_session: ContextVar[Optional[str]] = ContextVar("redis_current_session", default=None)


class RedisBackend(SessionBackend):
    
    def __init__(self, connection_manager: Any = None, ttl: int = 86400) -> None:
        self._connection_manager = connection_manager
        self.ttl = ttl
    
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        redis = await self._connection_manager.redis()
        data = await redis.get(f"session:{session_id}")
        return json.loads(data) if data else None
    
    async def set(self, session_id: str, data: Dict[str, Any]) -> None:
        redis = await self._connection_manager.redis()
        await redis.setex(
            f"session:{session_id}",
            self.ttl,
            json.dumps(data)
        )
    
    async def delete(self, session_id: str) -> None:
        redis = await self._connection_manager.redis()
        await redis.delete(f"session:{session_id}")
    
    async def exists(self, session_id: str) -> bool:
        redis = await self._connection_manager.redis()
        return await redis.exists(f"session:{session_id}") > 0
    
    def set_current(self, session_id: str) -> None:
        """Set current session ID in session-local context"""
        _current_session.set(session_id)
    
    def get_current(self) -> Optional[str]:
        """Get current session ID from session-local context"""
        return _current_session.get()
