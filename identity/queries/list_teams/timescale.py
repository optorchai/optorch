"""list teams - timescale"""

from typing import List, Dict, Any
from optorch.storage.queries.base import BaseQuery


class ListTeamsQuery(BaseQuery):
    """list teams for organization with pagination"""

    @property
    def query_name(self) -> str:
        return "identity.list_teams"

    async def execute(
        self,
        organization_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT id, organization_id, name, description, external_id, created_at, updated_at
            FROM teams
            WHERE organization_id = :organization_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """
        rows = await self.store.fetch_all(
            query,
            {
                "organization_id": organization_id,
                "limit": limit,
                "offset": offset,
            }
        )
        
        return [dict(row) for row in rows]
