from optorch.storage.queries.base import BaseQuery


class ResetUsageQuery(BaseQuery):
    """reset usage counter - timescale"""
    
    @property
    def query_name(self) -> str:
        return "reset_usage"
    
    async def execute(
        self,
        table_name: str,
        organization_id: str,
        metric: str,
        window: str,
        updated_at: str
    ) -> None:
        query = f"""
            UPDATE {table_name}
            SET count = 0, updated_at = :updated
            WHERE organization_id = :org_id AND metric = :metric AND window = :window
        """
        await self.store.execute(query, {
            "org_id": organization_id,
            "metric": metric,
            "window": window,
            "updated": updated_at
        })
