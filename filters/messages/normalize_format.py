"""Convert Message objects to dicts for LLM processing"""
from typing import List, Dict, Any, Union
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter


@register_filter("normalize_format")
class NormalizeFormatFilter(BaseFilter):
    """Convert Message objects to dicts"""
    
    def filter(self, messages: Union[List[Any], Any]) -> List[Dict[str, Any]]:
        """Convert Message objects to dict format"""

        if not isinstance(messages, list):
            messages = [messages]
        
        normalized = []
        for msg in messages:
            if hasattr(msg, 'to_dict'):
                normalized.append(msg.to_dict())
            else:
                normalized.append(msg)
        return normalized