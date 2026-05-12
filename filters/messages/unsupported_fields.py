"""Remove fields not supported by basic LLM APIs"""
from typing import Dict, Any, List, Union
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter


@register_filter("unsupported_fields")
class UnsupportedFieldsFilter(BaseFilter):
    """Remove fields not supported by basic LLM APIs (groq, etc)"""
    
    def filter(self, data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Filter unsupported fields from message data"""
        
        def clean_message(msg_dict: Dict[str, Any]) -> Dict[str, Any]:
            clean_msg = {
                "role": msg_dict.get("role"),
                "content": msg_dict.get("content")
            }
            
            for field in ["tool_call_id", "tool_calls", "name", "images"]:
                if field in msg_dict:
                    clean_msg[field] = msg_dict[field]
            
            return clean_msg
        
        if isinstance(data, list):
            return [clean_message(msg) for msg in data]
        else:
            return clean_message(data)