"""Instance-based filter pipeline"""
from typing import List, Any, Union
from optorch.filters.base_filter import BaseFilter
from optorch.filters.filter_registry import FilterRegistry


class FilterManager:
    """Instance-based filter pipeline with chainable add() and apply()"""
    
    def __init__(self):
        self._filter_list: List[BaseFilter] = []
    
    def add(self, filter: Union[str, BaseFilter], **kwargs) -> 'FilterManager':
        """Add filter to pipeline - chainable"""
        if isinstance(filter, str):
            filter_instance = FilterRegistry.create(filter, **kwargs)
        else:
            filter_instance = filter
        self._filter_list.append(filter_instance)
        return self
    
    def apply(self, data: Any) -> Any:
        """Apply all filters in sequence"""
        result = data
        for f in self._filter_list:
            result = f.filter(result)
        return result
    
    @classmethod
    def for_target(cls, domain: str, target: str, **kwargs) -> 'FilterManager':
        """Convenience factory - creates instance from domain.target config"""
        manager = cls()
        filter_names = FilterRegistry.get_target_filters(domain, target)
        for name in filter_names:
            if FilterRegistry.has(name):
                manager.add(name, **kwargs)
        return manager
    
    @property
    def filter_instances(self) -> List[BaseFilter]:
        """Access filter list"""
        return self._filter_list
