from typing import Dict, Any, Optional
from contextvars import ContextVar
from optorch.session.backends.base_backend import SessionBackend

_current_session: ContextVar[Optional[str]] = ContextVar("postgres_current_session", default=None)


class PostgresBackend(SessionBackend):
    
    def __init__(self, connection_manager: Any = None, table_name: str = "sessions") -> None:
        self._connection_manager = connection_manager
        self.table_name = table_name
    
    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        pool = await self._connection_manager.postgres()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT data FROM {self.table_name} WHERE session_id = $1",
                session_id
            )
            return row["data"] if row else None
    
    async def set(self, session_id: str, data: Dict[str, Any]) -> None:
        pool = await self._connection_manager.postgres()
        async with pool.acquire() as conn:
            await conn.execute(
                f"""
                INSERT INTO {self.table_name} (session_id, data, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (session_id)
                DO UPDATE SET data = $2, updated_at = NOW()
                """,
                session_id, data
            )
    
    async def delete(self, session_id: str) -> None:
        pool = await self._connection_manager.postgres()
        async with pool.acquire() as conn:
            await conn.execute(
                f"DELETE FROM {self.table_name} WHERE session_id = $1",
                session_id
            )
    
    async def exists(self, session_id: str) -> bool:
        pool = await self._connection_manager.postgres()
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT EXISTS(SELECT 1 FROM {self.table_name} WHERE session_id = $1)",
                session_id
            )
            return result
    
    def set_current(self, session_id: str) -> None:
        """Set current session ID in session-local context"""
        _current_session.set(session_id)
    
    def get_current(self) -> Optional[str]:
        """Get current session ID from session-local context"""
        return _current_session.get()
