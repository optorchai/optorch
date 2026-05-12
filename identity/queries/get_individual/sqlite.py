"""get individual - sqlite"""

import json
from typing import Optional
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import Individual, ContactMedium, OrganizationCharacteristic


class GetIndividualQuery(BaseQuery):
    """fetch individual by id"""

    @property
    def query_name(self) -> str:
        return "identity.get_individual"

    async def execute(self, user_id: str) -> Optional[Individual]:
        query = "SELECT * FROM individuals WHERE id = :id"
        row = await self.store.fetch_one(query, {"id": user_id})
        
        if not row:
            return None
        
        return Individual(
            id=row["id"],
            given_name=row["given_name"],
            family_name=row["family_name"],
            middle_name=row["middle_name"],
            title=row["title"],
            status=row["status"],
            contact=[ContactMedium(**c) for c in json.loads(row["contact"])],
            characteristic=[OrganizationCharacteristic(**c) for c in json.loads(row["characteristic"])],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
