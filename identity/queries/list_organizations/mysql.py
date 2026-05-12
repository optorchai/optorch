"""list organizations - mysql"""

import json
from typing import List
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import Organization, ContactMedium, OrganizationCharacteristic


class ListOrganizationsQuery(BaseQuery):
    """list all organizations with pagination"""

    @property
    def query_name(self) -> str:
        return "identity.list_organizations"

    async def execute(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str = "active",
    ) -> List[Organization]:
        query = """
            SELECT * FROM organizations
            WHERE status = :status
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """
        rows = await self.store.fetch_all(
            query,
            {
                "status": status,
                "limit": limit,
                "offset": offset,
            },
        )
        
        from optorch.identity.licensing.models import License
        
        orgs = []
        for row in rows:
            orgs.append(
                Organization(
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
            )
        return orgs
