"""list configs with optional prefix - timescale"""

from typing import Any, Dict, List, Optional
from optorch.storage.queries.base import BaseQuery


class ListConfigsQuery(BaseQuery):
    """list configs with optional prefix filter and tenant support
    
    returns tenant-specific configs if organization_id provided
    """
    
    @property
    def query_name(self) -> str:
        return "list_configs"
    
    async def execute(self, prefix: Optional[str] = None, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if organization_id:
            # tenant-specific configs + global configs
            if prefix:
                query = """
                    SELECT namespace, organization_id, config_data, updated_at 
                    FROM optorch_config 
                    WHERE namespace LIKE :pattern 
                      AND (organization_id = :organization_id OR organization_id IS NULL)
                      AND is_active = TRUE
                """
                rows = await self.store.fetch_all(query, {"pattern": f"{prefix}%", "organization_id": organization_id})
            else:
                query = """
                    SELECT namespace, organization_id, config_data, updated_at 
                    FROM optorch_config 
                    WHERE (organization_id = :organization_id OR organization_id IS NULL)
                      AND is_active = TRUE
                """
                rows = await self.store.fetch_all(query, {"organization_id": organization_id})
        else:
            # global configs only
            if prefix:
                query = """
                    SELECT namespace, organization_id, config_data, updated_at 
                    FROM optorch_config 
                    WHERE namespace LIKE :pattern 
                      AND organization_id IS NULL
                      AND is_active = TRUE
                """
                rows = await self.store.fetch_all(query, {"pattern": f"{prefix}%"})
            else:
                query = """
                    SELECT namespace, organization_id, config_data, updated_at 
                    FROM optorch_config 
                    WHERE organization_id IS NULL
                      AND is_active = TRUE
                """
                rows = await self.store.fetch_all(query)
        
        return [
            {
                "namespace": row["namespace"],
                "organization_id": row["organization_id"],
                "config_data": row["config_data"],
                "updated_at": row["updated_at"]
            }
            for row in rows
        ]
