from typing import Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetAllUsageQuery(BaseQuery):
    """get all metrics for organization - mysql"""
    
    @property
    def query_name(self) -> str:
        return "get_all_usage"
    
    async def execute(
        self,
        table_name: str,
        organization_id: str,
        window: str = "lifetime"
    ) -> list[Dict[str, Any]]:
        query = f"""
            SELECT metric, count FROM {table_name}
            WHERE organization_id = :org_id AND window = :window
        """
        return await self.store.fetch_all(query, {
            "org_id": organization_id,
            "window": window
        })
