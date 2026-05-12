"""create invite token - timescale"""

from optorch.storage.queries.base import BaseQuery
from datetime import datetime


class CreateInviteTokenQuery(BaseQuery):
    """store invite token for new user"""

    @property
    def query_name(self) -> str:
        return "identity.create_invite_token"

    async def execute(
        self, 
        token: str, 
        individual_id: str, 
        expiry: datetime,
        created_by: str
    ) -> None:
        query = """
            INSERT INTO invite_tokens (
                token, individual_id, status, expiry, created_at, created_by
            ) VALUES (
                :token, :individual_id, 'active', :expiry, CURRENT_TIMESTAMP, :created_by
            )
        """
        await self.store.execute(query, {
            "token": token,
            "individual_id": individual_id,
            "expiry": expiry,
            "created_by": created_by
        })
