import json
from optorch.storage.queries.base import BaseQuery


class SaveCasbinPolicyQuery(BaseQuery):
    """insert single Casbin policy into database"""
    
    @property
    def query_name(self) -> str:
        return "identity.save_casbin_policy"
    
    async def execute(self, ptype: str, rule: list[str], **kwargs):
        rule_json = json.dumps(rule)
        
        query = """
            INSERT INTO casbin_policies (ptype, rule)
            VALUES (:ptype, :rule)
        """
        await self.store.execute(query, {"ptype": ptype, "rule": rule_json})
