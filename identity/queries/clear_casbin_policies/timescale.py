from optorch.storage.queries.base import BaseQuery


class ClearCasbinPoliciesQuery(BaseQuery):
    """truncate all Casbin policies"""
    
    @property
    def query_name(self) -> str:
        return "identity.clear_casbin_policies"
    
    async def execute(self, **kwargs):
        query = "DELETE FROM casbin_policies"
        await self.store.execute(query, {})
