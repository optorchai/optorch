"""Vector store registry"""

from typing import Dict, Type
from optorch.embeddings.vector_stores.base import BaseVectorStore


class VectorStoreRegistry:
    _providers: Dict[str, Type[BaseVectorStore]] = {}
    _instances: Dict[str, BaseVectorStore] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: Type[BaseVectorStore]):
        cls._providers[name] = provider_class
    
    @classmethod
    def get(cls, name: str, embedding_provider, **kwargs) -> BaseVectorStore:
        """Get or create vector store instance - one per provider type"""
        if name not in cls._instances:
            if name not in cls._providers:
                raise ValueError(f"Vector store provider '{name}' not registered")
            cls._instances[name] = cls._providers[name](embedding_provider, **kwargs)
        return cls._instances[name]
    
    @classmethod
    def has(cls, name: str) -> bool:
        return name in cls._providers
