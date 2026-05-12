"""delete account lockout - sqlite"""

from optorch.storage.queries.base import BaseQuery


class DeleteAccountLockoutQuery(BaseQuery):
    """unlock account"""

    @property
    def query_name(self) -> str:
        return "identity.delete_account_lockout"

    async def execute(self, user_id: str) -> None:
        query = """
            DELETE FROM account_lockouts
            WHERE user_id = :user_id
        """
        await self.store.execute(query, {"user_id": user_id})
