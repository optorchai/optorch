"""get policy snapshot - mysql"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetPolicySnapshotQuery(BaseQuery):
    """fetch specific policy snapshot"""

    @property
    def query_name(self) -> str:
        return "identity.get_policy_snapshot"

    async def execute(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT snapshot_id, policies, description, created_at
            FROM policy_snapshots
            WHERE snapshot_id = :snapshot_id
        """
        row = await self.store.fetch_one(query, {"snapshot_id": snapshot_id})
        return dict(row) if row else None
