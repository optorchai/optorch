"""clear failed login attempts - timescale"""

from optorch.storage.queries.base import BaseQuery


class ClearFailedLoginAttemptsQuery(BaseQuery):
    """reset failed login counter"""

    @property
    def query_name(self) -> str:
        return "identity.clear_failed_login_attempts"

    async def execute(self, user_id: str) -> None:
        query = """
            DELETE FROM failed_login_attempts
            WHERE user_id = :user_id
        """
        await self.store.execute(query, {"user_id": user_id})
