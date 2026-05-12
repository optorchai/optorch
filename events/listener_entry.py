"""Listener entry dataclass with filters and metadata"""
from typing import Any, Optional, Set, Dict
from dataclasses import dataclass, field
from optorch.filters.filter_manager import FilterManager
from optorch.events.constants import Priority


@dataclass
class ListenerEntry:
    """Entry for a registered listener with routing metadata"""
    listener: Any
    priority: int = Priority.NORMAL
    tags: Optional[Set[str]] = None
    blocking: bool = False
    _filter_manager: FilterManager = field(default_factory=FilterManager)
    
    @property
    def filters(self) -> FilterManager:
        """access filter manager for registering routing filters"""
        return self._filter_manager
    
    def should_receive(self, event: Dict[str, Any]) -> bool:
        """check if listener should receive event via filter pipeline"""
        if not self._filter_manager.filter_instances:
            return True
        result = self._filter_manager.apply(event)
        return result is not None
    
    def has_any_tag(self, tags: Set[str]) -> bool:
        """check if listener matches any tag"""
        if self.tags is None:
            return True  # untagged listeners match all
        return bool(self.tags & tags)
