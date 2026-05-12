"""list audit logs - timescale"""

from typing import List, Dict, Any, Optional
from optorch.storage.queries.base import BaseQuery


class ListAuditLogsQuery(BaseQuery):
    """fetch authorization audit trail with filters"""

    @property
    def query_name(self) -> str:
        return "identity.list_audit_logs"

    async def execute(
        self,
        subject: Optional[str] = None,
        resource: Optional[str] = None,
        decision: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        conditions = []
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        
        if subject:
            conditions.append("subject = :subject")
            params["subject"] = subject
        
        if resource:
            conditions.append("resource = :resource")
            params["resource"] = resource
        
        if decision:
            conditions.append("decision = :decision")
            params["decision"] = decision
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        query = f"""
            SELECT subject, resource, action, decision, provider, reason, created_at
            FROM audit_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """
        
        rows = await self.store.fetch_all(query, params)
        return [dict(row) for row in rows]
