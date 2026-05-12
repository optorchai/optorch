"""delete individual - sqlite"""

from datetime import datetime, UTC
from optorch.storage.queries.base import BaseQuery


class DeleteIndividualQuery(BaseQuery):
    """soft delete individual"""

    @property
    def query_name(self) -> str:
        return "identity.delete_individual"

    async def execute(self, individual_id: str) -> None:
        query = """
            UPDATE individuals
            SET status = :status, updated_at = :updated_at
            WHERE id = :id
        """
        await self.store.execute(
            query,
            {
                "status": "deleted",
                "updated_at": datetime.now(UTC),
                "id": individual_id,
            },
        )
