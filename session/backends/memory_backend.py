from typing import Dict, Any, Optional
from contextvars import ContextVar
from optorch.session.backends.base_backend import SessionBackend

_memory_store: Dict[str, Dict[str, Any]] = {}
_current_session: ContextVar[Optional[str]] = ContextVar("current_session", default=None)


class MemoryBackend(SessionBackend):
    
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return _memory_store.get(session_id)
    
    async def set(self, session_id: str, data: Dict[str, Any]) -> None:
        _memory_store[session_id] = data
    
    async def delete(self, session_id: str) -> None:
        if session_id in _memory_store:
            del _memory_store[session_id]
    
    async def exists(self, session_id: str) -> bool:
        return session_id in _memory_store
    
    def set_current(self, session_id: str) -> None:
        """Set current session ID in session-local context"""
        _current_session.set(session_id)
    
    def get_current(self) -> Optional[str]:
        """Get current session ID from session-local context"""
        return _current_session.get()
    
    @staticmethod
    def clear_current() -> None:
        """Clear current session (testing only)"""
        _current_session.set(None)
    
    @staticmethod
    def current_session_id() -> Optional[str]:
        """Convenience static method for tools to access current session"""
        return _current_session.get()
    
    async def clear(self) -> None:
        """Clear all sessions (testing only)"""
        _memory_store.clear()
