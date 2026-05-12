"""create policy snapshot - sqlite"""

from optorch.storage.queries.base import BaseQuery


class CreatePolicySnapshotQuery(BaseQuery):
    """save policy snapshot"""

    @property
    def query_name(self) -> str:
        return "identity.create_policy_snapshot"

    async def execute(self, snapshot_id: str, policies: str, description: str = "") -> None:
        query = """
            INSERT INTO policy_snapshots (snapshot_id, policies, description)
            VALUES (:snapshot_id, :policies, :description)
        """
        await self.store.execute(query, {
            "snapshot_id": snapshot_id,
            "policies": policies,
            "description": description
        })
