"""get config by namespace - timescale"""

from typing import Any, Dict, Optional
from optorch.storage.queries.base import BaseQuery


class GetConfigQuery(BaseQuery):
    """fetch config by namespace with tenant support
    
    priority: tenant-specific > global (NULL org_id)
    """
    
    @property
    def query_name(self) -> str:
        return "get_config"
    
    async def execute(self, namespace: str, organization_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # try tenant-specific config first
        if organization_id:
            query = """
                SELECT namespace, organization_id, config_data, updated_at 
                FROM optorch_config 
                WHERE namespace = :namespace 
                  AND organization_id = :organization_id 
                  AND is_active = TRUE
            """
            row = await self.store.fetch_one(query, {"namespace": namespace, "organization_id": organization_id})
            if row:
                return {
                    "namespace": row["namespace"],
                    "organization_id": row["organization_id"],
                    "config_data": row["config_data"],  # JSONB auto-converts to dict
                    "updated_at": row["updated_at"]
                }
        
        # fallback to global config
        query = """
            SELECT namespace, organization_id, config_data, updated_at 
            FROM optorch_config 
            WHERE namespace = :namespace 
              AND organization_id IS NULL 
              AND is_active = TRUE
        """
        row = await self.store.fetch_one(query, {"namespace": namespace})
        if row:
            return {
                "namespace": row["namespace"],
                "organization_id": row["organization_id"],
                "config_data": row["config_data"],  # JSONB auto-converts to dict
                "updated_at": row["updated_at"]
            }
        return None
