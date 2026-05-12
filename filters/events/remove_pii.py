"""Remove personally identifiable information from events"""
from typing import Dict, Any, List, Optional
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter
from app.constants import FilterConstants


@register_filter("remove_pii")
class RemovePiiFilter(BaseFilter):
    """Remove personally identifiable information from events"""
    
    def __init__(self, sensitive_keys: Optional[List[str]] = None):
        self.sensitive_keys = sensitive_keys or ["email", "phone", "ssn", "credit_card", "password"]
    
    def filter(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact PII from event data"""
        filtered = event_data.copy()
        for key in self.sensitive_keys:
            if key in filtered:
                filtered[key] = FilterConstants.REDACTED
        return filtered