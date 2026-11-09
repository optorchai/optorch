from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
import asyncio

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.session.session_manager import SessionManager

class ConversationHistory:
    def __init__(self, storage: "StorageManager") -> None:
        self._storage = storage

    async def list(
        self,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return await self._storage.query(
            "get_conversations",
            organization_id=organization_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    async def get_messages(
        self,
        session_id: str,
        layer: str = "thread",
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        return await self._storage.query(
            "get_session_messages",
            session_id=session_id,
            layer=layer,
            limit=limit,
        )

    async def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        return await self._storage.query("get_conversation", session_id=session_id)

    async def resume(self, session_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        conversation, messages = await asyncio.gather(
            self.get(session_id),
            self.get_messages(session_id, layer="thread"),
        )

        return conversation, messages

    async def get_events(self, session_id: str, limit: int = 500) -> List[Dict[str, Any]]:
        return await self._storage.query("get_session_events", session_id=session_id, limit=limit)

    async def delete(self, session_id: str) -> None:
        await self._storage.query("delete_conversation", session_id=session_id)

    async def restore_to_session(self, session_id: str, session_manager: "SessionManager") -> int:
        existing = await session_manager.get_data(session_id)

        if existing and existing.get("messages"):
            return 0

        conversation, rows = await asyncio.gather(
            self.get(session_id),
            self.get_messages(session_id, layer="thread"),
        )

        if not rows:
            return 0

        session_data: Dict[str, Any] = {
            "messages": [{"id": r["id"], "role": r["role"], "content": r["content"]} for r in rows]
        }

        if conversation:
            metadata = conversation.get("metadata")

            if isinstance(metadata, str):
                try:
                    import json
                    metadata = json.loads(metadata)
                except (ValueError, TypeError):
                    metadata = None

            if isinstance(metadata, dict):
                persisted_state = metadata.get("persisted_state")

                if persisted_state:
                    session_data["__persisted_state__"] = persisted_state

        await session_manager.set_data(session_data, session_id)
        
        return len(rows)
