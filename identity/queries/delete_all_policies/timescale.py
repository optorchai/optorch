"""delete all policies - timescale"""

from optorch.storage.queries.base import BaseQuery


class DeleteAllPoliciesQuery(BaseQuery):
    """clear all authorization policies"""

    @property
    def query_name(self) -> str:
        return "identity.delete_all_policies"

    async def execute(self) -> None:
        query = "DELETE FROM policies"
        await self.store.execute(query, {})
