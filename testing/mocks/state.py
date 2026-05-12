from typing import List, Optional, Dict, Any


class MockStateContainer:
    
    def __init__(self, initial_data: Optional[Dict[str, Any]] = None):
        self._data = initial_data or {}
        self.access_log: List[str] = []
        self.write_log: List[tuple[str, Any]] = []
    
    def __getitem__(self, key: str) -> Any:
        self.access_log.append(key)
        return self._data.get(key)
    
    def __setitem__(self, key: str, value: Any):
        self.write_log.append((key, value))
        self._data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        self.access_log.append(key)
        return self._data.get(key, default)
    
    def __contains__(self, key: str) -> bool:
        return key in self._data
    
    def keys(self):
        return self._data.keys()
    
    def values(self):
        return self._data.values()
    
    def items(self):
        return self._data.items()
    
    def clear(self):
        self._data.clear()
        self.access_log.clear()
        self.write_log.clear()
    
    def assert_key_accessed(self, key: str):
        assert key in self.access_log, f"Key '{key}' was not accessed"
    
    def assert_key_written(self, key: str, value: Optional[Any] = None):
        written_keys = [k for k, v in self.write_log]
        assert key in written_keys, f"Key '{key}' was not written"
        
        if value is not None:
            written_values = [v for k, v in self.write_log if k == key]
            assert value in written_values, f"Value {value} not written to '{key}'"
