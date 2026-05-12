"""Minimize state size before persistence"""
from typing import Dict, Any
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter


@register_filter("compact_state")
class CompactStateFilter(BaseFilter):
    """Remove unnecessary fields to minimize storage"""
    
    def filter(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove transient/computed fields from state"""
        
        transient_keys = {"_cache", "_temp", "debug_info", "request_id", "trace_id"}
        
        return {
            key: value 
            for key, value in state_data.items() 
            if not key.startswith("_") and key not in transient_keys
        }
