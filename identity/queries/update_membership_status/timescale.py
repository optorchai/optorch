"""update membership status - timescale"""

from datetime import datetime, UTC
from optorch.storage.queries.base import BaseQuery


class UpdateMembershipStatusQuery(BaseQuery):
    """update membership status"""

    @property
    def query_name(self) -> str:
        return "identity.update_membership_status"

    async def execute(self, user_id: str, org_id: int, status: str) -> None:
        query = """
            UPDATE organization_memberships
            SET status = :status, updated_at = :updated_at
            WHERE individual_id = :user_id AND organization_id = :org_id
        """
        await self.store.execute(
            query,
            {
                "status": status,
                "updated_at": datetime.now(UTC),
                "user_id": user_id,
                "org_id": org_id,
            },
        )
