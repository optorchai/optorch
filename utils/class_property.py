from typing import Any, Callable, Generic, TypeVar, overload

T = TypeVar('T')

class ClassProperty(Generic[T]):
    """Descriptor for class-level properties that work with Python 3.11+"""
    
    def __init__(self, func: Callable[..., T]) -> None:
        self.func = func
        
    @overload
    def __get__(self, instance: None, owner: type) -> T: ...
    
    @overload  
    def __get__(self, instance: Any, owner: type) -> T: ...
        
    def __get__(self, instance: Any, owner: type) -> T:
        return self.func(owner)
        
    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
