"""delete policy - timescale"""

from optorch.storage.queries.base import BaseQuery


class DeletePolicyQuery(BaseQuery):
    """remove specific authorization policy"""

    @property
    def query_name(self) -> str:
        return "identity.delete_policy"

    async def execute(self, subject: str, resource: str, action: str) -> None:
        query = """
            DELETE FROM policies
            WHERE subject = :subject AND resource = :resource AND action = :action
        """
        await self.store.execute(query, {
            "subject": subject,
            "resource": resource,
            "action": action
        })
