"""update organization - timescale"""

import json
from datetime import datetime, UTC
from typing import Optional, List, Any
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import ContactMedium, OrganizationCharacteristic


class UpdateOrganizationQuery(BaseQuery):
    """update organization fields"""

    @property
    def query_name(self) -> str:
        return "identity.update_organization"

    async def execute(
        self,
        org_id: int,
        name: Optional[str] = None,
        href: Optional[str] = None,
        organization_type: Optional[str] = None,
        status: Optional[str] = None,
        parent_organization_id: Optional[int] = None,
        contact: Optional[List[ContactMedium]] = None,
        characteristic: Optional[List[OrganizationCharacteristic]] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        updates = []
        params: dict[str, Any] = {"id": org_id, "updated_at": datetime.now(UTC)}
        
        if name is not None:
            updates.append("name = :name")
            params["name"] = name
        
        if href is not None:
            updates.append("href = :href")
            params["href"] = href
        
        if organization_type is not None:
            updates.append("organization_type = :organization_type")
            params["organization_type"] = organization_type
        
        if status is not None:
            updates.append("status = :status")
            params["status"] = status
        
        if parent_organization_id is not None:
            updates.append("parent_id = :parent_id")
            params["parent_id"] = parent_organization_id
        
        if contact is not None:
            updates.append("contact = :contact")
            params["contact"] = json.dumps([c.model_dump() for c in contact])
        
        if characteristic is not None:
            updates.append("characteristic = :characteristic")
            params["characteristic"] = json.dumps([c.model_dump() for c in characteristic])
        
        if metadata is not None:
            updates.append("metadata = :metadata")
            params["metadata"] = json.dumps(metadata)
        
        if not updates:
            return
        
        updates.append("updated_at = :updated_at")
        query = f"UPDATE organizations SET {', '.join(updates)} WHERE id = :id"
        await self.store.execute(query, params)
