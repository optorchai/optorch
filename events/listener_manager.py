"""Listener registry for event system"""
from typing import Any, Dict, List, Optional, Set, Union
from optorch.events.listener_entry import ListenerEntry
from optorch.events.constants import Priority
from optorch.filters.base_filter import BaseFilter


class ListenerManager:
    """Registry of all event listeners"""
    
    def __init__(self):
        self._entries: List[ListenerEntry] = []
        self._listener_map: Dict[int, ListenerEntry] = {}
    
    def add(
        self,
        listener: Any,
        priority: int = Priority.NORMAL,
        tags: Optional[Set[str]] = None,
        event_filter: Optional[Union[BaseFilter, List[BaseFilter]]] = None,
        blocking: bool = False
    ) -> ListenerEntry:
        """register listener with optional filters"""
        listener_id = id(listener)
        if listener_id in self._listener_map:
            return self._listener_map[listener_id]
        
        entry = ListenerEntry(
            listener=listener,
            priority=priority,
            tags=tags,
            blocking=blocking
        )
        
        # add filters if provided
        if event_filter is not None:
            filters = event_filter if isinstance(event_filter, list) else [event_filter]
            for f in filters:
                entry.filters.add(f)
        
        self._listener_map[listener_id] = entry
        self._entries.append(entry)
        self._entries.sort(key=lambda e: e.priority)
        
        return entry
    
    def remove(self, listener: Any) -> None:
        """unregister listener"""
        listener_id = id(listener)
        if listener_id in self._listener_map:
            entry = self._listener_map.pop(listener_id)
            self._entries.remove(entry)
    
    def for_event(self, event: Dict[str, Any]) -> List[ListenerEntry]:
        """get listeners that should receive this event"""
        return [e for e in self._entries if e.should_receive(event)]
    
    def by_tags(self, tags: Set[str]) -> List[ListenerEntry]:
        """get listeners matching any tag"""
        return [e for e in self._entries if e.has_any_tag(tags)]
    
    def all(self) -> List[ListenerEntry]:
        """get all listeners sorted by priority"""
        return self._entries.copy()
    
    def get(self, listener: Any) -> Optional[ListenerEntry]:
        """get entry for specific listener"""
        return self._listener_map.get(id(listener))
