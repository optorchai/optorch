"""create membership - sqlite"""

import json
import secrets
from datetime import datetime, UTC
from optorch.storage.queries.base import BaseQuery


class CreateMembershipQuery(BaseQuery):
    """create organization membership for individual"""

    @property
    def query_name(self) -> str:
        return "identity.create_membership"

    async def execute(self, individual_id: str, organization_id: int, roles: list[str]) -> None:
        query = """
            INSERT INTO organization_memberships (
                id, individual_id, organization_id, roles, status, joined_at, updated_at
            ) VALUES (
                :id, :individual_id, :organization_id, :roles, 'active', :joined_at, :updated_at
            )
        """
        now = datetime.now(UTC).isoformat()
        await self.store.execute(query, {
            "id": f"membership-{secrets.token_urlsafe(12)}",
            "individual_id": individual_id,
            "organization_id": organization_id,
            "roles": json.dumps(roles),
            "joined_at": now,
            "updated_at": now
        })

