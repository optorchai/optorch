from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetUsageQuery(BaseQuery):
    """get current usage count - timescale"""
    
    @property
    def query_name(self) -> str:
        return "get_usage"
    
    async def execute(
        self,
        table_name: str,
        organization_id: str,
        metric: str,
        window: str
    ) -> Optional[Dict[str, Any]]:
        query = f"""
            SELECT count FROM {table_name}
            WHERE organization_id = :org_id AND metric = :metric AND window = :window
        """
        return await self.store.fetch_one(query, {
            "org_id": organization_id,
            "metric": metric,
            "window": window
        })
