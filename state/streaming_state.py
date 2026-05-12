from typing import Any, Dict, Optional, AsyncIterator, List, TYPE_CHECKING
from .base_state import BaseState

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext


class StreamingState(BaseState):
    """
    Streaming-capable state container.
    
    Combines regular state data with async streaming capabilities.
    """
    
    def __init__(self, data: Optional[Dict[str, Any]] = None, stream: Optional[AsyncIterator] = None):
        super().__init__()
        self._data: Dict[str, Any] = data or {}
        self._stream = stream
        if 'messages' not in self._data:
            self._data['messages'] = []
        if 'entities' not in self._data:
            self._data['entities'] = {}
    
    @property
    def stream(self) -> Optional[AsyncIterator]:
        """Get the streaming iterator"""
        return self._stream
    

    
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
        """Returns True if this state has a stream attached"""
        return self._stream is not None
    
    def set_stream(self, stream: AsyncIterator) -> 'StreamingState':
        """Set or update the stream"""
        self._stream = stream
        return self
    
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
        stream_info = f", streaming={self.is_streaming}" if self.is_streaming else ""
        return f"StreamingState({dict(self._data)}{stream_info})"