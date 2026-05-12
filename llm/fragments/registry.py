"""Registry for prompt fragments"""
from typing import Dict
from optorch.llm.fragments.base import Fragment


class FragmentRegistry:
    """Registry for prompt fragments"""
    
    def __init__(self):
        self._fragments: Dict[str, Fragment] = {}
    
    def register(self, fragment: Fragment):
        """Register a fragment"""
        self._fragments[fragment.name] = fragment
    
    def load_all(self) -> Dict[str, str]:
        """Load all fragment values"""
        return {name: fragment.get_value() for name, fragment in self._fragments.items()}
