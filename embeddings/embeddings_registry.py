from typing import Dict, Type
from .base import BaseEmbeddingProvider


class EmbeddingsRegistry:
    _providers: Dict[str, Type[BaseEmbeddingProvider]] = {}
    _instances: Dict[str, BaseEmbeddingProvider] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: Type[BaseEmbeddingProvider]):
        cls._providers[name] = provider_class
    
    @classmethod
    def get(cls, name: str, **kwargs) -> BaseEmbeddingProvider:
        if name not in cls._instances:
            if name not in cls._providers:
                raise ValueError(f"Embedding provider '{name}' not registered")
            cls._instances[name] = cls._providers[name](**kwargs)
        return cls._instances[name]
    
    @classmethod
    def has(cls, name: str) -> bool:
        return name in cls._providers
