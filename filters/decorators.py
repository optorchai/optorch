"""Decorators for filter registration"""
from typing import Type
from optorch.filters.base_filter import BaseFilter


def register_filter(name: str):
    """Decorator to register a filter class"""
    def decorator(filter_class: Type[BaseFilter]):
        from optorch.filters.filter_registry import FilterRegistry
        FilterRegistry.register(name, filter_class)
        return filter_class
    return decorator