"""get organization membership - timescale"""

import json
from typing import Optional
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import OrganizationMembership


class GetMembershipQuery(BaseQuery):
    """fetch membership for user in organization"""

    @property
    def query_name(self) -> str:
        return "identity.get_membership"

    async def execute(self, user_id: str, org_id: int) -> Optional[OrganizationMembership]:
        query = """
            SELECT * FROM organization_memberships
            WHERE individual_id = :user_id AND organization_id = :org_id
        """
        row = await self.store.fetch_one(query, {"user_id": user_id, "org_id": org_id})
        
        if not row:
            return None
        
        return OrganizationMembership(
            id=row["id"],
            user_id=row["individual_id"],
            organization_id=row["organization_id"],
            roles=json.loads(row["roles"]),
            status=row["status"],
            joined_at=row["joined_at"],
            created_at=row["joined_at"],
            updated_at=row["updated_at"],
        )
