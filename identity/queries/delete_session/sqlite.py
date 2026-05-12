"""delete session - sqlite"""

from optorch.storage.queries.base import BaseQuery


class DeleteSessionQuery(BaseQuery):
    """delete user session (logout)"""

    @property
    def query_name(self) -> str:
        return "identity.delete_session"

    async def execute(self, session_id: str) -> None:
        query = "DELETE FROM user_sessions WHERE session_id = :session_id"
        await self.store.execute(query, {"session_id": session_id})
