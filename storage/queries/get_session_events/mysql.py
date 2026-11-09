import json
from typing import Any, Dict, List
from optorch.storage.queries.base import BaseQuery
from optorch.logging import get_logger
from optorch.storage.queries.get_session_events import _created_at_to_ms

logger = get_logger(__name__)

_EXCLUDED_TYPES = frozenset({
    "authentication.provider_tried",
    "authentication.success",
    "authentication.failed",
    "authorization.deny",
    "authorization.policy_evaluated",
    "session.updated",
})


class GetSessionEventsQuery(BaseQuery):

    @property
    def query_name(self) -> str:
        return "get_session_events"

    async def execute(
        self,
        session_id: str,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        placeholders = ",".join(f"'{t}'" for t in _EXCLUDED_TYPES)
        query = f"""
            SELECT
                id, type, timestamp_ms, session_id,
                provider, model, input_tokens, output_tokens,
                duration_ms, cost, currency,
                node_name, phase, tool_name, metadata, created_at
            FROM events
            WHERE session_id = :session_id
              AND type NOT IN ({placeholders})
            ORDER BY timestamp_ms ASC, id ASC
            LIMIT :limit
        """

        rows = await self.store.fetch_all(query, {"session_id": session_id, "limit": limit})

        results = []
        for row in rows:
            item = dict(row)
            if item.get("metadata") and isinstance(item["metadata"], str):
                try:
                    item["metadata"] = json.loads(item["metadata"])
                except (ValueError, TypeError):
                    item["metadata"] = None

            results.append(item)

        caps_query = """
            SELECT m.id, m.node_name, m.capabilities, m.created_at
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.session_id = :session_id
              AND m.role = 'assistant'
              AND m.capabilities IS NOT NULL
              AND m.layer = 'thread'
        """
        cap_rows = await self.store.fetch_all(caps_query, {"session_id": session_id})

        for row in cap_rows:
            try:
                caps = json.loads(row["capabilities"]) if isinstance(row["capabilities"], str) else row["capabilities"]
            except (ValueError, TypeError):
                continue

            if not isinstance(caps, dict):
                continue
            
            for key, text in caps.items():
                results.append({
                    "id": f"{row['id']}:cap:{key}",
                    "type": f"llm.capability.{key}",
                    "timestamp_ms": _created_at_to_ms(row["created_at"]),
                    "session_id": session_id,
                    "provider": None,
                    "model": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "duration_ms": None,
                    "cost": None,
                    "currency": "USD",
                    "node_name": row["node_name"],
                    "phase": None,
                    "tool_name": None,
                    "metadata": {"content": text},
                    "created_at": row["created_at"],
                })

        return results
