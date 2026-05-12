from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """Base for embedding providers"""
    
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        pass
    
    @abstractmethod
    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Vector dimensions"""
        pass
