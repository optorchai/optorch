"""Storage event listener for persistent event storage

Uses storage manager to write events through query registry.
Supports all storage backends (TimescaleDB, SQLite, MySQL).
"""
import asyncio
import json
from typing import Dict, Any, TYPE_CHECKING
from decimal import Decimal
from optorch.events.listeners.base import BaseListener
from optorch.llm.pricing import Pricing
from optorch.utils.json_encoder import make_json_safe
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = get_logger(__name__)


class StorageListener(BaseListener):
    """writes events to storage backend via storage manager"""
    
    def __init__(self, storage_manager: 'StorageManager'):
        super().__init__()
        self._storage_manager = storage_manager
    
    @staticmethod
    def _json_serializer(obj):
        """convert non-JSON types using shared make_json_safe"""
        result = make_json_safe(obj)
        if result is obj and not isinstance(obj, (str, int, float, bool, type(None))):
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
        return result
    
    def on_event(self, event: Dict[str, Any]):
        """sync wrapper for async write (called from EventEmitter)"""
        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._async_write(event))
            task.add_done_callback(self._handle_write_error)
        except RuntimeError:
            logger.warning("no event loop for storage write - event dropped")
    
    def _handle_write_error(self, task: asyncio.Task):
        """log uncaught exceptions from async writes"""
        try:
            task.result()
        except Exception as e:
            logger.error(f"storage write failed: {e}", exc_info=True)
    
    async def _async_write(self, event: Dict[str, Any]):
        """actual async write via storage manager"""
        event_type = event.get("type", "unknown")
        timestamp_ms = int(event.get("timestamp", 0) * 1000) if "timestamp" in event else 0
        
        usage = event.get("usage")
        if usage and hasattr(usage, 'cost'):
            cost = event.get("cost") or getattr(usage, 'cost', None)
            currency = event.get("currency") or getattr(usage, 'currency', None) or Pricing.get_currency()
        else:
            cost = event.get("cost") or (usage.get("cost") if usage else None)
            currency = event.get("currency") or (usage.get("currency") if usage else None) or Pricing.get_currency()
        
        if cost is not None:
            cost = Decimal(str(cost))
        
        try:
            await self._storage_manager.query(
                "save_event",
                event_type=event_type,
                timestamp_ms=timestamp_ms,
                session_id=event.get("session_id"),
                request_id=event.get("request_id"),
                user_id=event.get("user_id"),
                application_id=event.get("application_id"),
                provider=event.get("provider"),
                model=event.get("model"),
                input_tokens=event.get("prompt_tokens") or event.get("input_tokens"),
                output_tokens=event.get("completion_tokens") or event.get("output_tokens"),
                duration_ms=event.get("duration_ms"),
                cost=cost,
                currency=currency,
                node_name=event.get("node_name"),
                phase=event.get("phase"),
                tool_name=event.get("tool_name"),
                metadata=json.dumps(event, default=self._json_serializer)
            )
        except Exception as e:
            logger.error(f"Storage write failed: {e}", exc_info=True)
