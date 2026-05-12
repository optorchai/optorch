"""
Instance-based SessionManager
Manages session state via pluggable backends (Memory, Redis, etc).
"""

from typing import Dict, Any, Optional, Callable, List, TYPE_CHECKING
from contextvars import ContextVar
import time
from optorch.logging import get_logger
from optorch.session.backends import SessionBackend
from optorch.constants import SessionBackends
from optorch.errors import SessionError

if TYPE_CHECKING:
    from optorch.config.manager import ConfigManager

_current_session: ContextVar[Optional[str]] = ContextVar('session_manager_current', default=None)

logger = get_logger(__name__)


class SessionManager:
    """
    Instance-based session management.
    Manages current session ID and delegates storage to backend.
    """
    
    def __init__(self, backend: SessionBackend, config_manager: Optional['ConfigManager'] = None):
        """
        Initialize session manager.
        
        Args:
            backend: Storage backend (MemoryBackend, RedisBackend, etc)
            config_manager: ConfigManager for passing to EventEmitter (creates new if None)
        """
        self._backend = backend
        self._last_activity: Dict[str, float] = {}
        self._event_config: Optional[Dict[str, Any]] = None
        self._cleanup_hooks: List[Callable[[str], Any]] = []
        self._config_manager = config_manager
    
    @classmethod
    def from_config(cls, config: Dict[str, Any], connection_manager: Any = None, config_manager: Optional['ConfigManager'] = None) -> 'SessionManager':
        """
        Create SessionManager from config.
        
        Args:
            config: Session configuration dict
                {
                    'backend': 'memory' | 'redis',
                    'memory': {...},
                    'redis': {...}
                }
            connection_manager: Optional connection manager for DB backends
            config_manager: ConfigManager for passing to EventEmitter
        
        Returns:
            Configured SessionManager instance
        """
        backend_type = config.get('backend', SessionBackends.MEMORY)
        backend_config = config.get(backend_type, {})
        
        backend = SessionBackend.create(backend_type, connection_manager, **backend_config)
        
        return cls(backend, config_manager=config_manager)
    
    def set_current_session(self, session_id: str) -> None:
        _current_session.set(session_id)
        self._backend.set_current(session_id)

    def get_id(self) -> Optional[str]:
        return _current_session.get()
    
    @staticmethod
    def current_session_id() -> Optional[str]:
        """Get current session ID without needing SessionManager instance
        
        For use in tools and other code that needs ambient session context.
        Returns None if no session is active in current async context.
        """
        return _current_session.get()
    
    async def get_data(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or _current_session.get()
        if not sid:
            raise SessionError("No session ID available")
        
        data = await self._backend.get(sid)
        if data is None:
            data = {}
        
        return data
    
    async def set_data(self, data: Dict[str, Any], session_id: Optional[str] = None) -> None:
        sid = session_id or _current_session.get()
        if not sid:
            raise SessionError("No session ID available")
        
        await self._backend.set(sid, data)
    
    async def delete(self, session_id: Optional[str] = None) -> None:
        sid = session_id or _current_session.get()
        if not sid:
            raise SessionError("No session ID available")
        
        for hook in self._cleanup_hooks:
            try:
                hook(sid)
            except Exception as e:
                logger.error(f"Cleanup hook {hook.__name__} failed for session {sid}: {e}")
        
        if sid in self._last_activity:
            del self._last_activity[sid]
        
        await self._backend.delete(sid)
    
    async def exists(self, session_id: str) -> bool:
        return await self._backend.exists(session_id)
    
    async def clear_all(self) -> None:
        """Clear all sessions (testing only - MemoryBackend specific)"""
        from optorch.session.backends import MemoryBackend
        if isinstance(self._backend, MemoryBackend):
            await self._backend.clear()
    
    def set_event_config(self, event_config: Dict[str, Any]) -> None:
        """store events config for lazy EventEmitter creation"""
        self._event_config = event_config
    
    def register_cleanup_hook(self, hook: Callable[[str], Any]) -> None:
        """register cleanup hook to run when session is deleted
        
        Args:
            hook: Callable that takes session_id and performs cleanup
        """
        self._cleanup_hooks.append(hook)
        logger.debug(f"Registered session cleanup hook: {hook.__name__}")
    
    async def cleanup_idle_sessions(self, idle_timeout: int = 3600) -> None:
        """
        Cleanup idle sessions.
        
        Args:
            idle_timeout: Seconds of inactivity before cleanup (default 1 hour)
        """
        now = time.time()
        closed = []
        
        for session_id, last_active in list(self._last_activity.items()):
            if now - last_active > idle_timeout:
                del self._last_activity[session_id]
                closed.append(session_id)
                logger.info(f"Cleaned up idle session {session_id}")
        
        if closed:
            logger.info(f"Cleaned up {len(closed)} idle sessions")
