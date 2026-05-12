"""revoke refresh token - mysql"""

from optorch.storage.queries.base import BaseQuery


class RevokeRefreshTokenQuery(BaseQuery):
    """revoke refresh token (optional tracking)"""

    @property
    def query_name(self) -> str:
        return "identity.revoke_refresh_token"

    async def execute(self, token_hash: str, expires_at: str) -> None:
        query = """
            UPDATE refresh_tokens 
            SET status = 'revoked',
                revoked_at = CURRENT_TIMESTAMP,
                expires_at = :expires_at
            WHERE token_hash = :token_hash
        """
        await self.store.execute(query, {"token_hash": token_hash, "expires_at": expires_at})
