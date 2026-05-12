"""get all members of organization - timescale"""

import json
from typing import List
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import OrganizationMembership


class GetOrgMembersQuery(BaseQuery):
    """fetch all members of organization"""

    @property
    def query_name(self) -> str:
        return "identity.get_org_members"

    async def execute(self, org_id: int) -> List[OrganizationMembership]:
        query = "SELECT * FROM organization_memberships WHERE organization_id = :org_id"
        rows = await self.store.fetch_all(query, {"org_id": org_id})
        
        members = []
        for row in rows:
            members.append(
                OrganizationMembership(
                    id=row["id"],
                    user_id=row["individual_id"],
                    organization_id=row["organization_id"],
                    roles=json.loads(row["roles"]),
                    status=row["status"],
                    joined_at=row["joined_at"],
                    created_at=row["joined_at"],
                    updated_at=row["updated_at"],
                )
            )
        return members
