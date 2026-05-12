"""create membership - mysql"""

import json
from optorch.storage.queries.base import BaseQuery


class CreateMembershipQuery(BaseQuery):
    """create organization membership for individual"""

    @property
    def query_name(self) -> str:
        return "identity.create_membership"

    async def execute(self, individual_id: str, organization_id: int, roles: list[str]) -> None:
        query = """
            INSERT INTO organization_memberships (
                individual_id, organization_id, roles, status, created_at, updated_at
            ) VALUES (
                :individual_id, :organization_id, :roles, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
        """
        await self.store.execute(query, {
            "individual_id": individual_id,
            "organization_id": organization_id,
            "roles": json.dumps(roles)
        })
