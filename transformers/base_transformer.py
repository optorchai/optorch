from abc import ABC, abstractmethod
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext


class BaseTransformer(ABC):
    """Base class for content transformers that clean/normalize LLM response text"""
    
    @abstractmethod
    async def transform(self, content: str, context: 'LLMContext') -> Dict[str, Any]:
        """Transform content string.
        
        Args:
            content: The response content string
            context: Full LLM context for state/events/metadata access
            
        Returns:
            Dict with 'content' (transformed string) and optional 'metadata' (extracted data)
        """
        pass
