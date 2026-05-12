"""list policies - sqlite"""

from typing import List, Dict, Any
from optorch.storage.queries.base import BaseQuery


class ListPoliciesQuery(BaseQuery):
    """fetch all authorization policies"""

    @property
    def query_name(self) -> str:
        return "identity.list_policies"

    async def execute(self) -> List[Dict[str, Any]]:
        query = """
            SELECT subject, resource, action, effect
            FROM policies
            ORDER BY subject, resource, action
        """
        rows = await self.store.fetch_all(query, {})
        return [dict(row) for row in rows]
