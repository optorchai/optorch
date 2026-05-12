"""get invite token - sqlite"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetInviteTokenQuery(BaseQuery):
    """fetch invite token data"""

    @property
    def query_name(self) -> str:
        return "identity.get_invite_token"

    async def execute(self, token: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT * FROM invite_tokens 
            WHERE token = :token 
            AND status = 'active'
            AND expiry > CURRENT_TIMESTAMP
        """
        row = await self.store.fetch_one(query, {"token": token})
        
        if not row:
            return None
        
        return dict(row)
