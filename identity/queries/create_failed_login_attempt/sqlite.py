"""create failed login attempt - sqlite"""

from optorch.storage.queries.base import BaseQuery


class CreateFailedLoginAttemptQuery(BaseQuery):
    """record failed login attempt"""

    @property
    def query_name(self) -> str:
        return "identity.create_failed_login_attempt"

    async def execute(self, user_id: str, reason: str = "invalid_credentials") -> None:
        query = """
            INSERT INTO failed_login_attempts (user_id, reason)
            VALUES (:user_id, :reason)
        """
        await self.store.execute(query, {
            "user_id": user_id,
            "reason": reason
        })
