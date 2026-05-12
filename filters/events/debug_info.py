"""Add debug context for development environment"""
from typing import Dict, Any
import os
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter
from optorch.utils.config import get_env


@register_filter("debug_info")
class DebugInfoFilter(BaseFilter):
    """Add debug context for development"""
    
    def filter(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add debug info in development mode"""        
        environment = get_env("OPTORCH_ENV", "production")
        
        if environment == "development":
            event_data["debug"] = {
                "process_id": os.getpid(),
                "session_id": id(event_data)
            }
        return event_data