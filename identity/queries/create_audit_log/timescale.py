"""create audit log - timescale"""

from optorch.storage.queries.base import BaseQuery


class CreateAuditLogQuery(BaseQuery):
    """record authorization decision for compliance"""

    @property
    def query_name(self) -> str:
        return "identity.create_audit_log"

    async def execute(
        self,
        subject: str,
        resource: str,
        action: str,
        decision: str,
        provider: str = "",
        reason: str = ""
    ) -> None:
        query = """
            INSERT INTO audit_logs (subject, resource, action, decision, provider, reason)
            VALUES (:subject, :resource, :action, :decision, :provider, :reason)
        """
        await self.store.execute(query, {
            "subject": subject,
            "resource": resource,
            "action": action,
            "decision": decision,
            "provider": provider,
            "reason": reason
        })
