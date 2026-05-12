"""invalidate reset token - mysql"""

from optorch.storage.queries.base import BaseQuery


class InvalidateResetTokenQuery(BaseQuery):
    """mark reset token as used"""

    @property
    def query_name(self) -> str:
        return "identity.invalidate_reset_token"

    async def execute(self, token: str) -> None:
        query = """
            UPDATE reset_tokens 
            SET status = 'used',
                used_at = CURRENT_TIMESTAMP
            WHERE token = :token
        """
        await self.store.execute(query, {"token": token})
