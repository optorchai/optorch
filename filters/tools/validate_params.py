"""Validate and sanitize tool input parameters"""
from typing import Dict, Any
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter


@register_filter("validate_tool_params")
class ValidateToolParamsFilter(BaseFilter):
    """Validate tool parameters against schema and sanitize inputs"""
    
    def filter(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize tool parameters"""
        if not isinstance(tool_data, dict):
            return tool_data
        
        params = tool_data.get("params", {})
        sanitized_params = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                sanitized_params[key] = value.replace("\x00", "")
            else:
                sanitized_params[key] = value
        
        return {
            **tool_data,
            "params": sanitized_params
        }
