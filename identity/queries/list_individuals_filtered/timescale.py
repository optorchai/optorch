"""list individuals with SCIM filtering - timescale"""

import json
from typing import List, Optional
from optorch.storage.queries.base import BaseQuery
from optorch.identity.organization.models import Individual, ContactMedium, OrganizationCharacteristic


class ListIndividualsFilteredQuery(BaseQuery):
    """list individuals with SCIM filter support"""

    @property
    def query_name(self) -> str:
        return "identity.list_individuals_filtered"

    async def execute(
        self,
        organization_id: Optional[str] = None,
        where_clause: str = "",
        filter_params: dict | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Individual], int]:
        """execute filtered list query
        
        Returns:
            (individuals, total_count)
        """
        filter_params = filter_params or {}
        
        base_where = "1=1"
        params = {}
        
        if organization_id:
            base_where += " AND om.organization_id = :org_id"
            params["org_id"] = organization_id
        
        if where_clause:
            base_where += f" AND ({where_clause})"
            params.update(filter_params)
        
        count_query = f"""
            SELECT COUNT(DISTINCT i.id) as total
            FROM individuals i
            LEFT JOIN organization_memberships om ON i.id = om.user_id
            WHERE {base_where}
        """
        
        count_row = await self.store.fetch_one(count_query, params)
        total = count_row["total"] if count_row else 0
        
        list_query = f"""
            SELECT DISTINCT i.*
            FROM individuals i
            LEFT JOIN organization_memberships om ON i.id = om.user_id
            WHERE {base_where}
            ORDER BY i.created_at DESC
            LIMIT :limit OFFSET :offset
        """
        
        params["limit"] = limit
        params["offset"] = offset
        
        rows = await self.store.fetch_all(list_query, params)
        
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
                    contact=[ContactMedium(**c) for c in json.loads(row["contact"] or "[]")],
                    characteristic=[
                        OrganizationCharacteristic(**c)
                        for c in json.loads(row["characteristic"] or "[]")
                    ],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        
        return individuals, total

