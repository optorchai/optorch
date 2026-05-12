"""get individual by email - timescale"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetIndividualByEmailQuery(BaseQuery):
    """fetch individual by email address"""

    @property
    def query_name(self) -> str:
        return "identity.get_individual_by_email"

    async def execute(self, email: str) -> Optional[Dict[str, Any]]:
        # simple email column search
        query = """
            SELECT * FROM individuals 
            WHERE email = :email 
            LIMIT 1
        """
        
        row = await self.store.fetch_one(query, {"email": email})
        
        if not row:
            return None
        
        return dict(row)
