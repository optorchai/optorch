"""list distinct roles from organization memberships - mysql"""

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
            SELECT DISTINCT role_member.role
            FROM organization_memberships,
                 JSON_TABLE(
                     roles,
                     '$[*]' COLUMNS (role VARCHAR(255) PATH '$')
                 ) AS role_member
            WHERE status = 'active'
            ORDER BY role_member.role
        """
        
        rows = await self.store.fetch_all(query)
        return [row["role"] for row in rows]
