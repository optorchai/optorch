"""get config timestamp for staleness check - timescale"""

from typing import Any, Dict, Optional
from optorch.storage.queries.base import BaseQuery


class GetConfigTimestampQuery(BaseQuery):
    """get config timestamp for cache staleness check with tenant support"""
    
    @property
    def query_name(self) -> str:
        return "get_config_timestamp"
    
    async def execute(self, namespace: str, organization_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # try tenant-specific first
        if organization_id:
            query = """
                SELECT updated_at 
                FROM optorch_config 
                WHERE namespace = :namespace 
                  AND organization_id = :organization_id 
                  AND is_active = TRUE
            """
            row = await self.store.fetch_one(query, {"namespace": namespace, "organization_id": organization_id})
            if row:
                return {"updated_at": row["updated_at"]}
        
        # fallback to global
        query = """
            SELECT updated_at 
            FROM optorch_config 
            WHERE namespace = :namespace 
              AND organization_id IS NULL 
              AND is_active = TRUE
        """
        row = await self.store.fetch_one(query, {"namespace": namespace})
        if row:
            return {"updated_at": row["updated_at"]}
        return None
