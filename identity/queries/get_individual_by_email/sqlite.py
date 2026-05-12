"""get individual by email - sqlite"""

import json
from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetIndividualByEmailQuery(BaseQuery):
    """fetch individual by email address"""

    @property
    def query_name(self) -> str:
        return "identity.get_individual_by_email"

    async def execute(self, email: str) -> Optional[Dict[str, Any]]:
        # simplified schema has email column directly
        query = """
            SELECT * FROM individuals 
            WHERE email = :email AND deleted_at IS NULL
            LIMIT 1
        """
        row = await self.store.fetch_one(query, {"email": email})
        
        if not row:
            return None
        
        result = dict(row)
        
        # parse JSON fields
        if result.get("metadata") and isinstance(result["metadata"], str):
            result["metadata"] = json.loads(result["metadata"])
        if result.get("roles") and isinstance(result["roles"], str):
            result["roles"] = json.loads(result["roles"])
        if result.get("entitlements") and isinstance(result["entitlements"], str):
            result["entitlements"] = json.loads(result["entitlements"])
        
        return result
