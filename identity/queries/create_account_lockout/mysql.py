"""create account lockout - mysql"""

from datetime import datetime
from optorch.storage.queries.base import BaseQuery


class CreateAccountLockoutQuery(BaseQuery):
    """lock account until timestamp"""

    @property
    def query_name(self) -> str:
        return "identity.create_account_lockout"

    async def execute(self, user_id: str, locked_until: datetime, reason: str = "max_failed_attempts") -> None:
        query = """
            INSERT INTO account_lockouts (user_id, locked_until, reason)
            VALUES (:user_id, :locked_until, :reason)
            ON DUPLICATE KEY UPDATE locked_until = :locked_until, reason = :reason
        """
        await self.store.execute(query, {
            "user_id": user_id,
            "locked_until": locked_until,
            "reason": reason
        })
