from typing import Any, Type, TypeVar, Generic

T = TypeVar("T")


class Registry(Generic[T]):
    def __init__(self) -> None:
        self._items: dict[str, T] = {}
    
    def register(self, key: str, item: T) -> None:
        self._items[key] = item
    
    def get(self, key: str) -> T:
        if key not in self._items:
            raise KeyError(f"Item not registered: {key}")
        return self._items[key]
    
    def get_optional(self, key: str) -> T | None:
        return self._items.get(key)
    
    def has(self, key: str) -> bool:
        return key in self._items
    
    def unregister(self, key: str) -> None:
        self._items.pop(key, None)
    
    def list_keys(self) -> list[str]:
        return list(self._items.keys())
    
    def clear(self):
        self._items.clear()
