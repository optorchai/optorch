"""get scim token - sqlite"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetScimTokenQuery(BaseQuery):
    """retrieve scim token data"""

    @property
    def query_name(self) -> str:
        return "identity.get_scim_token"

    async def execute(self, token: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT token, organization_id, created_at, expires_at
            FROM scim_tokens
            WHERE token = :token
        """
        row = await self.store.fetch_one(query, {"token": token})
        
        if not row:
            return None
        
        return {
            "token": row["token"],
            "organization_id": row["organization_id"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
        }
