"""find child organizations - mysql"""

import json
from typing import List
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import Organization, ContactMedium, OrganizationCharacteristic


class FindOrganizationsByParentQuery(BaseQuery):
    """find all child organizations"""

    @property
    def query_name(self) -> str:
        return "identity.find_organizations_by_parent"

    async def execute(self, parent_id: int) -> List[Organization]:
        query = "SELECT * FROM organizations WHERE parent_organization_id = :parent_id"
        rows = await self.store.fetch_all(query, {"parent_id": parent_id})
        
        from optorch.identity.licensing.models import License
        
        orgs = []
        for row in rows:
            orgs.append(
                Organization(
                    id=row["id"],
                    name=row["name"],
                    organization_type=row["organization_type"],
                    status=row["status"],
                    parent_organization_id=row["parent_organization_id"],
                    license=License(**json.loads(row["license"])) if row["license"] else None,
                    characteristic=[OrganizationCharacteristic(**c) for c in json.loads(row["characteristic"])],
                    contact=[ContactMedium(**c) for c in json.loads(row["contact"])],
                    metadata=json.loads(row["metadata"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return orgs
