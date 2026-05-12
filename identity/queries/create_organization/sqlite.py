"""create organization - sqlite"""

import json
from typing import Optional
from optorch.storage.queries.base import BaseQuery
from optorch.errors import StateError
from optorch.identity.organization.models import Organization, ContactMedium, OrganizationCharacteristic


class CreateOrganizationQuery(BaseQuery):
    """create new organization"""

    @property
    def query_name(self) -> str:
        return "identity.create_organization"

    async def execute(
        self,
        name: str,
        href: Optional[str] = None,
        organization_type: str = "Company",
        status: str = "active",
        parent_id: Optional[int] = None,
        license: Optional[str] = None,
        contact: Optional[str] = None,
        characteristic: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Organization:
        query = """
            INSERT INTO organizations (
                name, href, organization_type, status, parent_id, license, contact, characteristic, metadata
            ) VALUES (
                :name, :href, :organization_type, :status, :parent_id, :license, :contact, :characteristic, :metadata
            )
            RETURNING *
        """
        
        row = await self.store.fetch_one(
            query,
            {
                "name": name,
                "href": href,
                "organization_type": organization_type,
                "status": status,
                "parent_id": parent_id,
                "license": license,
                "contact": contact,
                "characteristic": characteristic,
                "metadata": json.dumps(metadata) if metadata else "{}",
            },
        )
        
        if not row:
            raise StateError("failed to retrieve created organization")
        
        from optorch.identity.licensing.models import License
        
        return Organization(
            id=row["id"],
            name=row["name"],
            href=row.get("href"),
            organization_type=row.get("organization_type", "Company"),
            status=row.get("status", "active"),
            parent_organization_id=row.get("parent_id"),
            license=License(**json.loads(row["license"])) if row.get("license") else None,
            characteristic=[OrganizationCharacteristic(**c) for c in json.loads(row["characteristic"])] if row.get("characteristic") else [],
            contact=[ContactMedium(**c) for c in json.loads(row["contact"])] if row.get("contact") else [],
            metadata=json.loads(row["metadata"]) if row.get("metadata") else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

