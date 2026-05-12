"""count teams - mysql"""

from optorch.storage.queries.base import BaseQuery


class CountTeamsQuery(BaseQuery):
    """count total teams for organization"""

    @property
    def query_name(self) -> str:
        return "identity.count_teams"

    async def execute(self, organization_id: str) -> int:
        query = """
            SELECT COUNT(*) as count
            FROM teams
            WHERE organization_id = :organization_id
        """
        row = await self.store.fetch_one(query, {"organization_id": organization_id})
        
        return row["count"] if row else 0
