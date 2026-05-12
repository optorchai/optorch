"""get account lockout - mysql"""

from typing import Optional, Dict, Any
from optorch.storage.queries.base import BaseQuery


class GetAccountLockoutQuery(BaseQuery):
    """check if account is locked"""

    @property
    def query_name(self) -> str:
        return "identity.get_account_lockout"

    async def execute(self, user_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT user_id, locked_until, reason, created_at
            FROM account_lockouts
            WHERE user_id = :user_id
        """
        row = await self.store.fetch_one(query, {"user_id": user_id})
        return dict(row) if row else None
