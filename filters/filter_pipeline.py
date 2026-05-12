"""Chainable filter pipeline for composing filters"""
from typing import List, Any
from optorch.filters.base_filter import BaseFilter


class FilterPipeline(BaseFilter):
    """Chain multiple filters together"""
    
    def __init__(self, filters: List[BaseFilter]):
        self.filters = filters
    
    def filter(self, data: Any) -> Any:
        """Apply all filters in sequence"""
        result = data
        for f in self.filters:
            result = f.filter(result)
        return result
    
    def add(self, filter: BaseFilter) -> "FilterPipeline":
        """Add filter to pipeline (chainable)"""
        self.filters.append(filter)
        return self
    
    def __or__(self, other: BaseFilter) -> "FilterPipeline":
        """Enable pipe operator: filter1 | filter2"""
        return FilterPipeline(self.filters + [other])