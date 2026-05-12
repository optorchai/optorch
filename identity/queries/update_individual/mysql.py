"""update individual - mysql"""

import json
from datetime import datetime, UTC
from typing import Optional, List, Any
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import ContactMedium, OrganizationCharacteristic


class UpdateIndividualQuery(BaseQuery):
    """update individual fields"""

    @property
    def query_name(self) -> str:
        return "identity.update_individual"

    async def execute(
        self,
        individual_id: str,
        given_name: Optional[str] = None,
        family_name: Optional[str] = None,
        middle_name: Optional[str] = None,
        title: Optional[str] = None,
        status: Optional[str] = None,
        contact: Optional[List[ContactMedium]] = None,
        characteristic: Optional[List[OrganizationCharacteristic]] = None,
    ) -> None:
        updates = []
        params: dict[str, Any] = {"id": individual_id, "updated_at": datetime.now(UTC)}
        
        if given_name is not None:
            updates.append("given_name = :given_name")
            params["given_name"] = given_name
        
        if family_name is not None:
            updates.append("family_name = :family_name")
            params["family_name"] = family_name
        
        if middle_name is not None:
            updates.append("middle_name = :middle_name")
            params["middle_name"] = middle_name
        
        if title is not None:
            updates.append("title = :title")
            params["title"] = title
        
        if status is not None:
            updates.append("status = :status")
            params["status"] = status
        
        if contact is not None:
            updates.append("contact = :contact")
            params["contact"] = json.dumps([c.model_dump() for c in contact])
        
        if characteristic is not None:
            updates.append("characteristic = :characteristic")
            params["characteristic"] = json.dumps([c.model_dump() for c in characteristic])
        
        if not updates:
            return
        
        updates.append("updated_at = :updated_at")
        query = f"UPDATE individuals SET {', '.join(updates)} WHERE id = :id"
        await self.store.execute(query, params)
