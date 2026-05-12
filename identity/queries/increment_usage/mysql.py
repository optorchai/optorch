from optorch.storage.queries.base import BaseQuery


class IncrementUsageQuery(BaseQuery):
    """increment usage counter - mysql upsert"""
    
    @property
    def query_name(self) -> str:
        return "increment_usage"
    
    async def execute(
        self,
        table_name: str,
        organization_id: str,
        metric: str,
        window: str,
        amount: int,
        updated_at: str
    ) -> None:
        query = f"""
            INSERT INTO {table_name} (organization_id, metric, window, count, updated_at)
            VALUES (:org_id, :metric, :window, :amount, :updated)
            ON DUPLICATE KEY UPDATE
                count = count + :amount,
                updated_at = :updated
        """
        await self.store.execute(query, {
            "org_id": organization_id,
            "metric": metric,
            "window": window,
            "amount": amount,
            "updated": updated_at
        })
