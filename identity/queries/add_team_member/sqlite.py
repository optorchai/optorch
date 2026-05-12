"""add team member - sqlite"""

from datetime import datetime, UTC
from optorch.storage.queries.base import BaseQuery


class AddTeamMemberQuery(BaseQuery):
    """add member to team"""

    @property
    def query_name(self) -> str:
        return "identity.add_team_member"

    async def execute(self, team_id: str, user_id: str) -> None:
        now = datetime.now(UTC)
        query = """
            INSERT OR IGNORE INTO team_members (team_id, user_id, added_at)
            VALUES (:team_id, :user_id, :added_at)
        """
        await self.store.execute(
            query,
            {
                "team_id": team_id,
                "user_id": user_id,
                "added_at": now,
            },
        )
