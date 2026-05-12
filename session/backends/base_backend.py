from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class SessionBackend(ABC):
    
    @classmethod
    def create(cls, backend_type: str, connection_manager: Any = None, **kwargs: Any) -> "SessionBackend":
        from optorch.constants import SessionBackends
        from .memory_backend import MemoryBackend
        from .postgres_backend import PostgresBackend
        from .redis_backend import RedisBackend
        
        if backend_type == SessionBackends.MEMORY:
            return MemoryBackend()
        elif backend_type == SessionBackends.POSTGRES:
            table_name = kwargs.get("table_name", "sessions")
            return PostgresBackend(connection_manager, table_name)
        elif backend_type == SessionBackends.REDIS:
            ttl = kwargs.get("ttl", 86400)
            return RedisBackend(connection_manager, ttl)
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")
    
    @abstractmethod
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def set(self, session_id: str, data: Dict[str, Any]) -> None:
        pass
    
    @abstractmethod
    async def delete(self, session_id: str) -> None:
        pass
    
    @abstractmethod
    async def exists(self, session_id: str) -> bool:
        pass
    
    @abstractmethod
    def set_current(self, session_id: str) -> None:
        """Set current session ID in session-local context"""
        pass
    
    @abstractmethod
    def get_current(self) -> Optional[str]:
        """Get current session ID from session-local context"""
        pass
