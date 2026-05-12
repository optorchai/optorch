"""Bridge between Message system and SessionManager"""

from typing import List, Optional
from optorch.messaging import Message, MessageContext
from optorch.messaging.source import MessageSource
from optorch.session.session_manager import SessionManager
from optorch.errors import ConfigurationError


class SessionMessageSource(MessageSource):
    
    def __init__(self, session_manager: Optional[SessionManager] = None) -> None:
        if session_manager is None:
            raise ConfigurationError("SessionManager instance required")
        self._session_manager = session_manager
    
    async def get(self, context: MessageContext) -> List[Message]:
        data = await self._session_manager.get_data(context.session_id)
        if not data:
            return []
        
        raw = data.get("messages", [])
        return [Message.from_dict(msg) for msg in raw]
    
    async def save(self, messages: List[Message], context: MessageContext) -> None:
        data = await self._session_manager.get_data(context.session_id) or {}
        existing = data.get("messages", [])
        existing_ids = {msg.get("id") for msg in existing if isinstance(msg, dict) and "id" in msg}
        new_messages = [msg.to_dict() for msg in messages if msg.id not in existing_ids]
        data["messages"] = existing + new_messages
        await self._session_manager.set_data(data, context.session_id)
