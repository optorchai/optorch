"""Sanitize tool output before returning to LLM"""
from typing import Any, Dict
from optorch.filters.base_filter import BaseFilter
from optorch.filters.decorators import register_filter


@register_filter("sanitize_tool_output")
class SanitizeToolOutputFilter(BaseFilter):
    """Sanitize tool output to prevent injection attacks"""
    
    def filter(self, result: Any) -> Any:
        """Sanitize tool result"""
        if isinstance(result, str):
            return "".join(char for char in result if char.isprintable() or char in "\n\t")
        
        if isinstance(result, dict):
            return {k: self.filter(v) for k, v in result.items()}
        
        if isinstance(result, list):
            return [self.filter(item) for item in result]
        
        return result
