"""create revoked token entry - mysql"""

from datetime import datetime
from optorch.storage.queries.base import BaseQuery


class CreateRevokedTokenQuery(BaseQuery):
    """record token revocation"""

    @property
    def query_name(self) -> str:
        return "identity.create_revoked_token"

    async def execute(self, jti: str, revoked_at: datetime, expires_at: datetime) -> None:
        query = """
            INSERT INTO revoked_tokens (jti, revoked_at, expires_at)
            VALUES (:jti, :revoked_at, :expires_at)
        """
        await self.store.execute(query, {
            "jti": jti,
            "revoked_at": revoked_at,
            "expires_at": expires_at
        })
