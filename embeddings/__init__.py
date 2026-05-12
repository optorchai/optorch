"""
Shared embeddings package.

Usage:
    from optorch.embeddings import EmbeddingsRegistry
    from optorch.embeddings.providers import OpenAIEmbeddingProvider
    
    EmbeddingsRegistry.register("openai", OpenAIEmbeddingProvider)
    provider = EmbeddingsRegistry.get("openai", model="text-embedding-3-small")
    
    embeddings = await provider.embed(["hello", "world"])
"""

from .base import BaseEmbeddingProvider
from .embeddings_registry import EmbeddingsRegistry
from .embedding_config import EmbeddingConfig
from .vector_store import VectorStore
from .vector_store_registry import VectorStoreRegistry
from .vector_stores.base import BaseVectorStore

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingsRegistry",
    "EmbeddingConfig",
    "VectorStore",
    "VectorStoreRegistry",
    "BaseVectorStore"
]
