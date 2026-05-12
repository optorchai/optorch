"""check revoked token - mysql"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class CheckRevokedTokenQuery(BaseQuery):
    """check if token is revoked"""

    @property
    def query_name(self) -> str:
        return "identity.check_revoked_token"

    async def execute(self, token_hash: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT * FROM refresh_tokens 
            WHERE token_hash = :token_hash 
            AND status = 'revoked'
            LIMIT 1
        """
        row = await self.store.fetch_one(query, {"token_hash": token_hash})
        
        if not row:
            return None
        
        return dict(row)
