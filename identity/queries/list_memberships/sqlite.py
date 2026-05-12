"""list memberships - sqlite"""

import json
from typing import List
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import OrganizationMembership


class ListMembershipsQuery(BaseQuery):
    """list all memberships for individual"""

    @property
    def query_name(self) -> str:
        return "identity.list_memberships"

    async def execute(self, individual_id: str) -> List[OrganizationMembership]:
        query = "SELECT * FROM organization_memberships WHERE individual_id = :individual_id ORDER BY joined_at DESC"
        rows = await self.store.fetch_all(query, {"individual_id": individual_id})
        
        memberships = []
        for row in rows:
            memberships.append(
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
        return memberships
