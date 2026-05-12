"""Extension lifecycle registry"""

from typing import Optional, Callable, Awaitable, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ExtensionState:
    """State container for a registered extension"""
    name: str
    cleanup: Optional[Callable[[], Awaitable[None]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExtensionRegistry:
    """
    Registry for optorch extensions with lifecycle management
    
    provides type-safe registration and cleanup for extensions
    """
    
    def __init__(self):
        self._extensions: Dict[str, ExtensionState] = {}
    
    def register(
        self, 
        name: str,
        cleanup: Optional[Callable[[], Awaitable[None]]] = None,
        **metadata: Any
    ) -> None:
        """
        Register an extension with optional cleanup handler
        
        args:
            name: extension identifier
            cleanup: async cleanup function called on shutdown
            **metadata: additional extension metadata
        """
        self._extensions[name] = ExtensionState(
            name=name,
            cleanup=cleanup,
            metadata=metadata
        )
    
    def get(self, name: str) -> Optional[ExtensionState]:
        """Get extension state by name"""
        return self._extensions.get(name)
    
    async def cleanup_all(self) -> None:
        """Call all registered cleanup handlers"""
        for ext in self._extensions.values():
            if ext.cleanup:
                try:
                    await ext.cleanup()
                except Exception:
                    pass
    
    def __iter__(self):
        """Iterate over registered extensions"""
        return iter(self._extensions.values())
    
    def __len__(self) -> int:
        """Number of registered extensions"""
        return len(self._extensions)
