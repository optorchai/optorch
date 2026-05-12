"""create team - timescale"""

from typing import Dict, Any, Optional
from datetime import datetime, UTC
from optorch.storage.queries.base import BaseQuery


class CreateTeamQuery(BaseQuery):
    """create new team"""

    @property
    def query_name(self) -> str:
        return "identity.create_team"

    async def execute(
        self,
        team_id: str,
        organization_id: str,
        name: str,
        description: Optional[str] = None,
        external_id: Optional[str] = None
    ) -> Dict[str, Any]:
        now = datetime.now(UTC)
        query = """
            INSERT INTO teams (
                id, organization_id, name, description, external_id, created_at, updated_at
            ) VALUES (
                :id, :organization_id, :name, :description, :external_id, :created_at, :updated_at
            )
        """
        await self.store.execute(
            query,
            {
                "id": team_id,
                "organization_id": organization_id,
                "name": name,
                "description": description,
                "external_id": external_id,
                "created_at": now,
                "updated_at": now,
            },
        )
        
        return {
            "id": team_id,
            "organization_id": organization_id,
            "name": name,
            "description": description,
            "external_id": external_id,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
