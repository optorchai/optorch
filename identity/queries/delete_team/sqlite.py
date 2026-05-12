"""delete team - sqlite"""

from optorch.storage.queries.base import BaseQuery


class DeleteTeamQuery(BaseQuery):
    """delete team and all memberships"""

    @property
    def query_name(self) -> str:
        return "identity.delete_team"

    async def execute(self, team_id: str) -> None:
        # delete members first
        await self.store.execute(
            "DELETE FROM team_members WHERE team_id = :team_id",
            {"team_id": team_id}
        )
        
        # delete team
        await self.store.execute(
            "DELETE FROM teams WHERE id = :team_id",
            {"team_id": team_id}
        )
