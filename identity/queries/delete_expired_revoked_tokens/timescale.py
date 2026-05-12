"""delete expired revoked tokens - timescale"""

from datetime import datetime
from optorch.storage.queries.base import BaseQuery


class DeleteExpiredRevokedTokensQuery(BaseQuery):
    """cleanup expired revoked tokens"""

    @property
    def query_name(self) -> str:
        return "identity.delete_expired_revoked_tokens"

    async def execute(self, now: datetime) -> dict:
        query = """
            DELETE FROM revoked_tokens
            WHERE expires_at < :now
        """
        result = await self.store.execute(query, {"now": now})
        return {"deleted_count": getattr(result, 'rowcount', 0) if result is not None else 0}
