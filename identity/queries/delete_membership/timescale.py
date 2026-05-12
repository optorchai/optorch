"""delete membership - timescale"""

from optorch.storage.queries.base import BaseQuery


class DeleteMembershipQuery(BaseQuery):
    """hard delete membership"""

    @property
    def query_name(self) -> str:
        return "identity.delete_membership"

    async def execute(self, user_id: str, org_id: int) -> None:
        query = """
            DELETE FROM organization_memberships
            WHERE individual_id = :user_id AND organization_id = :organization_id
        """
        await self.store.execute(
            query,
            {
                "user_id": user_id,
                "organization_id": org_id,
            },
        )
