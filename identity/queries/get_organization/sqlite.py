"""get organization - sqlite"""

import json
from typing import Optional
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import Organization, ContactMedium, OrganizationCharacteristic


class GetOrganizationQuery(BaseQuery):
    """fetch organization by id"""

    @property
    def query_name(self) -> str:
        return "identity.get_organization"

    async def execute(self, organization_id: int) -> Optional[Organization]:
        query = "SELECT * FROM organizations WHERE id = :id"
        row = await self.store.fetch_one(query, {"id": organization_id})
        
        if not row:
            return None
        
        from optorch.identity.licensing.models import License
        
        return Organization(
            id=row["id"],
            name=row["name"],
            href=row.get("href"),
            organization_type=row.get("organization_type", "Company"),
            status=row.get("status", "active"),
            parent_organization_id=row.get("parent_organization_id"),
            license=License(**json.loads(row["license"])) if row.get("license") else None,
            characteristic=[OrganizationCharacteristic(**c) for c in json.loads(row["characteristic"])] if row.get("characteristic") else [],
            contact=[ContactMedium(**c) for c in json.loads(row["contact"])] if row.get("contact") else [],
            metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
