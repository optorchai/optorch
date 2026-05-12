"""create reset token - mysql"""

from optorch.storage.queries.base import BaseQuery
from datetime import datetime


class CreateResetTokenQuery(BaseQuery):
    """store password reset token"""

    @property
    def query_name(self) -> str:
        return "identity.create_reset_token"

    async def execute(
        self, 
        token: str, 
        individual_id: str, 
        expiry: datetime
    ) -> None:
        query = """
            INSERT INTO reset_tokens (
                token, individual_id, status, expiry, created_at
            ) VALUES (
                :token, :individual_id, 'active', :expiry, CURRENT_TIMESTAMP
            )
        """
        await self.store.execute(query, {
            "token": token,
            "individual_id": individual_id,
            "expiry": expiry
        })
