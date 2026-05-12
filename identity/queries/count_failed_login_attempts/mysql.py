"""count failed login attempts - mysql"""

from datetime import datetime
from optorch.storage.queries.base import BaseQuery


class CountFailedLoginAttemptsQuery(BaseQuery):
    """count failed attempts in time window"""

    @property
    def query_name(self) -> str:
        return "identity.count_failed_login_attempts"

    async def execute(self, user_id: str, since: datetime) -> int:
        query = """
            SELECT COUNT(*) as count
            FROM failed_login_attempts
            WHERE user_id = :user_id AND created_at >= :since
        """
        row = await self.store.fetch_one(query, {
            "user_id": user_id,
            "since": since
        })
        return row["count"] if row else 0
