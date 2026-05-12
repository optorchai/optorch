from typing import Any, Dict, Optional, List
from decimal import Decimal
from .base_state import BaseState


class State(BaseState):
    """
    Workflow state container that flows through orchestration.
    
    Dict-like interface with extensibility for app-specific state management.
    """
    
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        super().__init__()
        self._data: Dict[str, Any] = data or {}
        if 'messages' not in self._data:
            self._data['messages'] = []
        if 'entities' not in self._data:
            self._data['entities'] = {}
        if 'budget' not in self._data:
            self._data['budget'] = {
                'request_consumed': Decimal("0"),
                'session_consumed': Decimal("0")
            }
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> 'BaseState':
        self._data[key] = value
        return self
    
    def update(self, data: Dict[str, Any]) -> 'BaseState':
        self._data.update(data)
        return self
    
    def merge(self, other: 'BaseState') -> 'BaseState':
        other_data = getattr(other, '_data', None)
        if other_data is not None and hasattr(other_data, 'update'):
            self._data.update(other_data)
        else:
            other_dict = other.to_dict()
            self._data.update(other_dict)
        return self
    
    def has(self, key: str) -> bool:
        return key in self._data
    
    def remove(self, key: str) -> 'BaseState':
        self._data.pop(key, None)
        return self
    
    def add_message(self, role: str, content: str, **kwargs) -> None:
        from optorch.messaging import Message
        messages = self._data.get('messages', [])
        messages.append(Message(role=role, content=content, **kwargs))
        self._data['messages'] = messages
    
    def get_messages(self) -> List:
        from optorch.messaging import Message
        messages = self._data.get('messages', [])
        return [Message.from_dict(m) if isinstance(m, dict) else m for m in messages]
    
    def to_dict(self) -> Dict[str, Any]:
        from optorch.messaging import Message
        
        result = {}
        for key, value in self._data.items():
            if isinstance(value, Message):
                result[key] = value.to_dict()
            elif isinstance(value, list):
                result[key] = [item.to_dict() if isinstance(item, Message) else item for item in value]
            else:
                result[key] = value
        return result
    
    @property
    def is_streaming(self) -> bool:
        """Non-streaming state always returns False"""
        return False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'State':
        return cls(data)
    
    def __getitem__(self, key: str) -> Any:
        return self._data[key]
    
    def __setitem__(self, key: str, value: Any):
        self._data[key] = value
    
    def __contains__(self, key: str) -> bool:
        return key in self._data
    
    def __getattr__(self, key: str) -> Any:
        if key.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")
        return self._data.get(key)
    
    def __setattr__(self, key: str, value: Any):
        if key.startswith('_'):
            object.__setattr__(self, key, value)
        else:
            self._data[key] = value
    
    def __repr__(self) -> str:
        return f"State({self._data})"
