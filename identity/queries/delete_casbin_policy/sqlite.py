import json
from optorch.storage.queries.base import BaseQuery


class DeleteCasbinPolicyQuery(BaseQuery):
    """remove specific Casbin policy from database"""
    
    @property
    def query_name(self) -> str:
        return "identity.delete_casbin_policy"
    
    async def execute(self, ptype: str, rule: list[str], **kwargs):
        rule_json = json.dumps(rule)
        
        query = """
            DELETE FROM casbin_policies
            WHERE ptype = :ptype AND rule = :rule
        """
        await self.store.execute(query, {"ptype": ptype, "rule": rule_json})
