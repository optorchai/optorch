"""Event type pattern matching filter"""
from typing import Dict, Any, Optional, List
import fnmatch
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter


@register_filter("event_type_pattern")
class EventTypePatternFilter(BaseFilter):
    """filter events by type pattern matching (e.g., 'llm.*', '*.complete')"""
    
    def __init__(self, patterns: List[str]):
        """
        Args:
            patterns: list of fnmatch patterns (e.g., ['llm.*', 'node.*'])
        """
        self.patterns = patterns if isinstance(patterns, list) else [patterns]
    
    def filter(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """return event if type matches any pattern, else None"""
        event_type = data.get("type", "")
        
        for pattern in self.patterns:
            if fnmatch.fnmatch(event_type, pattern):
                return data
        
        return None
    
    def __repr__(self) -> str:
        return f"EventTypePatternFilter(patterns={self.patterns})"
