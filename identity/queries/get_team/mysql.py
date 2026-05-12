"""get team - mysql"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetTeamQuery(BaseQuery):
    """fetch team by ID"""

    @property
    def query_name(self) -> str:
        return "identity.get_team"

    async def execute(self, team_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT id, organization_id, name, description, external_id, created_at, updated_at
            FROM teams 
            WHERE id = :team_id
        """
        row = await self.store.fetch_one(query, {"team_id": team_id})
        
        if not row:
            return None
        
        return dict(row)
