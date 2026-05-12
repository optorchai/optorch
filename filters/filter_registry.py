"""Global catalog of filter classes and domain/target configuration"""
from typing import Dict, List, Type
from optorch.registry import Registry
from optorch.filters.base_filter import BaseFilter
from optorch.errors import ConfigurationError


class FilterRegistry:
    """Global registry for filter classes and domain/target mappings"""
    
    _filters = Registry[Type[BaseFilter]]()
    _domain_targets: Dict[str, Dict[str, List[str]]] = {}
    
    @classmethod
    def register(cls, name: str, filter_class: Type[BaseFilter]) -> None:
        """Register filter class by name"""
        cls._filters.register(name, filter_class)
    
    @classmethod
    def has(cls, name: str) -> bool:
        """Check if filter exists"""
        return cls._filters.has(name)
    
    @classmethod
    def get(cls, name: str) -> Type[BaseFilter]:
        """Get filter class by name"""
        return cls._filters.get(name)
    
    @classmethod
    def list_keys(cls) -> List[str]:
        """List all registered filter names"""
        return cls._filters.list_keys()
    
    @classmethod
    def create(cls, name: str, **kwargs) -> BaseFilter:
        """Create filter instance with kwargs"""
        if not cls.has(name):
            raise ConfigurationError(f"Unknown filter: {name}")
        filter_class = cls.get(name)
        return filter_class(**kwargs)
    
    @classmethod
    def register_target(cls, domain: str, target: str, filter_names: List[str]) -> None:
        """Register which filters apply to domain.target"""
        if domain not in cls._domain_targets:
            cls._domain_targets[domain] = {}
        cls._domain_targets[domain][target] = filter_names
    
    @classmethod
    def get_target_filters(cls, domain: str, target: str) -> List[str]:
        """Get filter names registered for domain.target"""
        return cls._domain_targets.get(domain, {}).get(target, [])
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registrations - test use only"""
        cls._filters.clear()
        cls._domain_targets.clear()
