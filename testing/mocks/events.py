from typing import Dict, Any, List, Optional
from optorch.events.event_emitter import EventEmitter


class EventCapture:
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self._original_emit = None
    
    def start(self):
        original_emit = EventEmitter.emit
        self._original_emit = original_emit
        events = self.events
        
        @classmethod
        def capture_emit(cls, event_type: str, data: Optional[Dict[str, Any]] = None):
            events.append({
                "type": event_type,
                "data": data or {}
            })
            original_emit(event_type, data)
        
        EventEmitter.emit = capture_emit  # type: ignore[method-assign]
        return self
    
    def stop(self):
        if self._original_emit:
            EventEmitter.emit = self._original_emit
        return self
    
    def __enter__(self):
        return self.start()
    
    def __exit__(self, *args):
        self.stop()
    
    def clear(self):
        self.events.clear()
    
    def count(self, event_type: str) -> int:
        return len([e for e in self.events if e["type"] == event_type])
    
    def get(self, event_type: str, index: int = 0) -> Optional[Dict[str, Any]]:
        matches = [e for e in self.events if e["type"] == event_type]
        return matches[index] if index < len(matches) else None
    
    def get_all(self, event_type: str) -> List[Dict[str, Any]]:
        return [e for e in self.events if e["type"] == event_type]
    
    def assert_emitted(self, event_type: str, times: Optional[int] = None):
        actual = self.count(event_type)
        if times is not None:
            assert actual == times, f"Expected {times} '{event_type}' events, got {actual}"
        else:
            assert actual > 0, f"Expected at least one '{event_type}' event, got none"
    
    def assert_not_emitted(self, event_type: str):
        count = self.count(event_type)
        assert count == 0, f"Expected no '{event_type}' events, got {count}"
    
    def assert_event_data(self, event_type: str, key: str, value: Any):
        event = self.get(event_type)
        assert event is not None, f"No '{event_type}' event found"
        assert key in event["data"], f"Key '{key}' not in event data"
        assert event["data"][key] == value, f"Expected {value}, got {event['data'][key]}"
