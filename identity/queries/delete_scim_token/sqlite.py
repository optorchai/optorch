"""delete scim token - sqlite"""

from optorch.storage.queries.base import BaseQuery


class DeleteScimTokenQuery(BaseQuery):
    """delete scim token"""

    @property
    def query_name(self) -> str:
        return "identity.delete_scim_token"

    async def execute(self, token: str) -> None:
        query = "DELETE FROM scim_tokens WHERE token = :token"
        await self.store.execute(query, {"token": token})
