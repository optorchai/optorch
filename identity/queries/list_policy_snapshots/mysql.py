"""list policy snapshots - mysql"""

from typing import List, Dict, Any
from optorch.storage.queries.base import BaseQuery


class ListPolicySnapshotsQuery(BaseQuery):
    """fetch all policy snapshots"""

    @property
    def query_name(self) -> str:
        return "identity.list_policy_snapshots"

    async def execute(self) -> List[Dict[str, Any]]:
        query = """
            SELECT snapshot_id, description, created_at
            FROM policy_snapshots
            ORDER BY created_at DESC
        """
        rows = await self.store.fetch_all(query, {})
        return [dict(row) for row in rows]
