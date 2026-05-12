import json
from optorch.storage.queries.base import BaseQuery


class ListCasbinPoliciesQuery(BaseQuery):
    """fetch all Casbin policies from database"""
    
    @property
    def query_name(self) -> str:
        return "identity.list_casbin_policies"
    
    async def execute(self, **kwargs):
        query = """
            SELECT ptype, rule 
            FROM casbin_policies
            ORDER BY id
        """
        rows = await self.store.fetch_all(query, {})
        
        return [
            {
                "ptype": row["ptype"],
                "rule": json.loads(row["rule"]) if row["rule"] else []
            }
            for row in rows
        ]
