"""Add session context to events for tracking"""
from typing import Dict, Any
import time
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter
from optorch.session.session_manager import SessionManager


@register_filter("add_session_context")
class AddSessionContextFilter(BaseFilter):
    """Add session context to events"""
    
    def filter(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add session and timestamp context"""

        if "session_id" not in event_data:
            session_id = SessionManager.current_session_id()

            if session_id:
                event_data["session_id"] = session_id
            else:
                event_data["session_id"] = "unknown"
        
        event_data["timestamp"] = time.time()
        return event_data