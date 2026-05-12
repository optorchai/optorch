"""remove team member - timescale"""

from optorch.storage.queries.base import BaseQuery


class RemoveTeamMemberQuery(BaseQuery):
    """remove member from team"""

    @property
    def query_name(self) -> str:
        return "identity.remove_team_member"

    async def execute(self, team_id: str, user_id: str) -> None:
        query = """
            DELETE FROM team_members 
            WHERE team_id = :team_id AND user_id = :user_id
        """
        await self.store.execute(query, {"team_id": team_id, "user_id": user_id})
