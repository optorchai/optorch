"""Remove sensitive data before state persistence"""
from typing import Dict, Any, List, Optional
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter
from app.constants import FilterConstants


@register_filter("redact_sensitive_state")
class RedactSensitiveStateFilter(BaseFilter):
    """Redact sensitive fields before saving state"""
    
    def __init__(self, sensitive_keys: Optional[List[str]] = None):
        self.sensitive_keys = sensitive_keys or [
            "api_key", "password", "token", "secret", "credit_card", 
            "ssn", "auth", "credential", "private_key"
        ]
    
    def filter(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields from state"""
        filtered = {}
        
        for key, value in state_data.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_keys):
                filtered[key] = FilterConstants.REDACTED
            elif isinstance(value, dict):
                filtered[key] = self.filter(value)
            elif isinstance(value, list):
                filtered[key] = [self.filter(item) if isinstance(item, dict) else item for item in value]
            else:
                filtered[key] = value
        
        return filtered
