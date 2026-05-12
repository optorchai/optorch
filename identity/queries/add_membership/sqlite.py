"""add organization membership - sqlite"""

import json
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import OrganizationMembership


class AddMembershipQuery(BaseQuery):
    """add organization membership"""

    @property
    def query_name(self) -> str:
        return "identity.add_membership"

    async def execute(self, membership: OrganizationMembership) -> None:
        query = """
            INSERT INTO organization_memberships (
                id, individual_id, organization_id, roles,
                status, joined_at, updated_at
            ) VALUES (
                :id, :individual_id, :org_id, :roles,
                :status, :joined_at, :updated_at
            )
        """
        await self.store.execute(
            query,
            {
                "id": membership.id,
                "individual_id": membership.user_id,
                "org_id": membership.organization_id,
                "roles": json.dumps(membership.roles),
                "status": membership.status,
                "joined_at": membership.joined_at,
                "updated_at": membership.updated_at,
            },
        )
