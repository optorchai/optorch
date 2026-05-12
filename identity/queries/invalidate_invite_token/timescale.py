"""invalidate invite token - timescale"""

from optorch.storage.queries.base import BaseQuery


class InvalidateInviteTokenQuery(BaseQuery):
    """mark invite token as used"""

    @property
    def query_name(self) -> str:
        return "identity.invalidate_invite_token"

    async def execute(self, token: str) -> None:
        query = """
            UPDATE invite_tokens 
            SET status = 'used',
                used_at = CURRENT_TIMESTAMP
            WHERE token = :token
        """
        await self.store.execute(query, {"token": token})
