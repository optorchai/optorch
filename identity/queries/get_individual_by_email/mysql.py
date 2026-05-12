"""get individual by email - mysql"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetIndividualByEmailQuery(BaseQuery):
    """fetch individual by email address"""

    @property
    def query_name(self) -> str:
        return "identity.get_individual_by_email"

    async def execute(self, email: str) -> Optional[Dict[str, Any]]:
        # individuals table has contact JSON array with email addresses
        # search for email in JSON contact array
        query = """
            SELECT * FROM individuals 
            WHERE JSON_SEARCH(contact, 'one', :email) IS NOT NULL
            LIMIT 1
        """
        row = await self.store.fetch_one(query, {"email": email})
        
        if not row:
            return None
        
        return dict(row)
