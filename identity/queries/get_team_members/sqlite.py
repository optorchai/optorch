"""get team members - sqlite"""

from typing import List, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetTeamMembersQuery(BaseQuery):
    """fetch all members of a team"""

    @property
    def query_name(self) -> str:
        return "identity.get_team_members"

    async def execute(self, team_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT 
                tm.user_id,
                i.given_name || ' ' || i.family_name as name,
                tm.added_at
            FROM team_members tm
            LEFT JOIN individuals i ON tm.user_id = i.id
            WHERE tm.team_id = :team_id
            ORDER BY tm.added_at
        """
        rows = await self.store.fetch_all(query, {"team_id": team_id})
        
        return [dict(row) for row in rows]
