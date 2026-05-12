from abc import ABC, abstractmethod
from typing import Any

class PromptProvider(ABC):
    """Base class for prompt providers."""
    
    @abstractmethod
    async def load(self, prompt_name: str, fragments: dict[str, Any]) -> str | None:
        """Load a prompt template.
        
        Args:
            prompt_name: Name of the prompt to load
            fragments: Dict of fragment values to inject
            
        Returns:
            ChatPromptTemplate if successful, None if not found/failed
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        pass
