from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, TYPE_CHECKING
from optorch.messaging import Message

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext


class BaseState(ABC):
    """Base class for all state implementations."""
    
    # LLM context for deferred callbacks - managed by node lifecycle
    _llm_context: Optional['LLMContext'] = None
    
    def __init__(self):
        pass
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> 'BaseState':
        """Set value by key"""
        pass
    
    @abstractmethod
    def update(self, data: Dict[str, Any]) -> 'BaseState':
        """Update with dictionary data"""
        pass
    
    @abstractmethod
    def merge(self, other: 'BaseState') -> 'BaseState':
        """Merge with another state"""
        pass
    
    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if key exists"""
        pass
    
    @abstractmethod
    def remove(self, key: str) -> 'BaseState':
        """Remove key"""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        pass
    

    
    @property
    @abstractmethod
    def is_streaming(self) -> bool:
        """Check if this state supports streaming"""
        pass
    
    # Message helpers
    @abstractmethod
    def add_message(self, role: str, content: str, **kwargs) -> None:
        """Add a message to state"""
        pass
    
    @abstractmethod
    def get_messages(self) -> List['Message']:
        """Get all messages"""
        pass
    
    def get_messages_as_dicts(self) -> List[Dict[str, Any]]:
        """Get messages as dicts"""
        return [m.to_dict() for m in self.get_messages()]
    
    # Entity helpers
    def set_entity(self, entity_type: str, data: Any) -> None:
        """Set entity data"""
        entities = self.get('entities', {})
        entities[entity_type] = data
        self.set('entities', entities)
    
    def get_entity(self, entity_type: str) -> Any:
        """Get entity data"""
        return self.get('entities', {}).get(entity_type)
    
    def has_entity(self, entity_type: str) -> bool:
        """Check if entity exists"""
        return entity_type in self.get('entities', {})
    
    def pop(self, key: str, default: Any = None) -> Any:
        """Remove and return value by key"""
        value = self.get(key, default)
        self.remove(key)
        return value
    
    # Dict-like access
    def __getitem__(self, key: str) -> Any:
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        return self.has(key)