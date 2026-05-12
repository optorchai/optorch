"""delete organization - timescale"""

from datetime import datetime, UTC
from optorch.storage.queries.base import BaseQuery


class DeleteOrganizationQuery(BaseQuery):
    """soft delete organization"""

    @property
    def query_name(self) -> str:
        return "identity.delete_organization"

    async def execute(self, org_id: int) -> None:
        query = """
            UPDATE organizations
            SET status = :status, updated_at = :updated_at
            WHERE id = :id
        """
        await self.store.execute(
            query,
            {
                "status": "deleted",
                "updated_at": datetime.now(UTC),
                "id": org_id,
            },
        )
