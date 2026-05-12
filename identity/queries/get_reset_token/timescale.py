"""get reset token - timescale"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetResetTokenQuery(BaseQuery):
    """fetch password reset token data"""

    @property
    def query_name(self) -> str:
        return "identity.get_reset_token"

    async def execute(self, token: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT * FROM reset_tokens 
            WHERE token = :token 
            AND status = 'active'
            AND expiry > CURRENT_TIMESTAMP
        """
        row = await self.store.fetch_one(query, {"token": token})
        
        if not row:
            return None
        
        return dict(row)
