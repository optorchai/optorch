from typing import Any, Dict, Optional
from optorch.storage.queries.base import BaseQuery
from optorch.logging import get_logger

logger = get_logger(__name__)


class SaveEventQuery(BaseQuery):
    """save event to events table - sqlite"""
    
    @property
    def query_name(self) -> str:
        return "save_event"
    
    async def execute(
        self,
        event_type: str,
        timestamp_ms: int,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        application_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        duration_ms: Optional[int] = None,
        cost: Optional[float] = None,
        currency: str = "USD",
        node_name: Optional[str] = None,
        phase: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """insert event into events table"""
        
        query = """
            INSERT INTO events (
                type, timestamp_ms, session_id, request_id, user_id, application_id,
                provider, model, input_tokens, output_tokens, duration_ms, cost, currency,
                node_name, phase, tool_name, metadata
            ) VALUES (
                :type, :timestamp_ms, :session_id, :request_id, :user_id, :application_id,
                :provider, :model, :input_tokens, :output_tokens, :duration_ms, :cost, :currency,
                :node_name, :phase, :tool_name, :metadata
            )
        """
        
        values = {
            "type": event_type,
            "timestamp_ms": timestamp_ms,
            "session_id": session_id,
            "request_id": request_id,
            "user_id": user_id,
            "application_id": application_id,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "duration_ms": duration_ms,
            "cost": cost,
            "currency": currency,
            "node_name": node_name,
            "phase": phase,
            "tool_name": tool_name,
            "metadata": metadata
        }
        
        await self.store.execute(query, values)
        logger.debug(f"saved event: {event_type} for session {session_id}")
