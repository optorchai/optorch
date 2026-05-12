"""get JWT key rotation state - sqlite"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetJwtKeysQuery(BaseQuery):
    """fetch current JWT key rotation state"""

    @property
    def query_name(self) -> str:
        return "identity.get_jwt_keys"

    async def execute(self) -> Optional[Dict[str, Any]]:
        query = """
            SELECT keys_json, updated_at
            FROM jwt_keys
            ORDER BY updated_at DESC
            LIMIT 1
        """
        row = await self.store.fetch_one(query, {})
        
        if not row:
            return None
        
        return dict(row)
