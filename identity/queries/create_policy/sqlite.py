"""create policy - sqlite"""

from optorch.storage.queries.base import BaseQuery


class CreatePolicyQuery(BaseQuery):
    """insert authorization policy"""

    @property
    def query_name(self) -> str:
        return "identity.create_policy"

    async def execute(self, subject: str, resource: str, action: str, effect: str = "allow") -> None:
        query = """
            INSERT INTO policies (subject, resource, action, effect)
            VALUES (:subject, :resource, :action, :effect)
        """
        await self.store.execute(query, {
            "subject": subject,
            "resource": resource,
            "action": action,
            "effect": effect
        })
