"""list distinct roles from organization memberships - sqlite"""

from typing import Any
from optorch.storage.queries.base import BaseQuery


class ListRolesQuery(BaseQuery):
    """get all unique roles assigned across organization memberships"""

    @property
    def query_name(self) -> str:
        return "identity.list_roles"

    async def execute(self) -> list[str]:
        """return list of unique role names"""
        query = """
            SELECT DISTINCT json_each.value as role
            FROM organization_memberships,
                 json_each(organization_memberships.roles)
            WHERE status = 'active'
            ORDER BY role
        """
        
        rows = await self.store.fetch_all(query)
        return [row["role"] for row in rows]
