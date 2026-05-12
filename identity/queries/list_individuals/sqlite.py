"""list individuals - sqlite"""

import json
from typing import List
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import Individual, ContactMedium, OrganizationCharacteristic


class ListIndividualsQuery(BaseQuery):
    """list all individuals with pagination"""

    @property
    def query_name(self) -> str:
        return "identity.list_individuals"

    async def execute(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str = "active",
    ) -> List[Individual]:
        query = """
            SELECT * FROM individuals
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
        
        individuals = []
        for row in rows:
            individuals.append(
                Individual(
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
            )
        return individuals
