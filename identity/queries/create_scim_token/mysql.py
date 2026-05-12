"""create scim token - mysql"""

from datetime import datetime, UTC
from optorch.storage.queries.base import BaseQuery


class CreateScimTokenQuery(BaseQuery):
    """store scim token"""

    @property
    def query_name(self) -> str:
        return "identity.create_scim_token"

    async def execute(self, token: str, organization_id: str, created_at: datetime) -> None:
        query = """
            INSERT INTO scim_tokens (token, organization_id, created_at)
            VALUES (:token, :organization_id, :created_at)
        """
        await self.store.execute(
            query,
            {
                "token": token,
                "organization_id": organization_id,
                "created_at": created_at,
            },
        )
