"""Base class for prompt fragments"""

from typing import Optional

class Fragment:
    """Prompt fragment - can be static or dynamic (subclass for dynamic)"""
    
    def __init__(self, name: Optional[str] = None, content: Optional[str] = None) -> None:
        """
        Create a static fragment with name and content.
        For dynamic fragments, subclass and override get_value().
        
        Args:
            name: Placeholder name (e.g., 'tone', 'routing')
            content: Static content to inject
        """
        self._name = name
        self._content = content
    
    @property
    def name(self) -> str:
        """Fragment placeholder name (e.g., 'routing', 'tone')"""
        if self._name is not None:
            return self._name
        raise NotImplementedError("Subclasses must override name property")
    
    def get_value(self) -> str:
        """Generate fragment value (static or dynamic)"""
        if self._content is not None:
            return self._content
        raise NotImplementedError("Subclasses must override get_value()")
    
    def set_value(self, value: str) -> None:
        """Set fragment content (override for dynamic fragments)"""
        self._content = value
