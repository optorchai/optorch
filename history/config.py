"""History configuration"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class VectorConfig(BaseModel):
    """vector storage config"""
    provider: str = Field(
        default="qdrant",
        description="vector DB provider (qdrant, chromadb, pinecone, weaviate, or custom)"
    )
    collection_name: str = Field(
        default="optorch_history",
        description="collection/index name"
    )
    distance_metric: Literal["cosine", "l2", "ip"] = Field(
        default="cosine",
        description="distance metric for similarity search"
    )
    params: Dict[str, Any] = Field(
        default_factory=lambda: {"host": "localhost", "port": 6333},
        description="provider-specific parameters"
    )


class EmbeddingConfig(BaseModel):
    """embedding provider config"""
    provider: str = Field(
        default="ollama",
        description="embedding provider (ollama, openai, cohere, or custom)"
    )
    model: str = Field(
        default="nomic-embed-text",
        description="embedding model name"
    )
    dimensions: Optional[int] = Field(
        default=None,
        description="embedding dimensions - None = model default"
    )
    batch_size: int = Field(
        default=100,
        description="batch size for embedding generation"
    )
    params: Dict[str, Any] = Field(
        default_factory=lambda: {"base_url": "http://localhost:11434"},
        description="provider-specific parameters"
    )


class HistoryLayerConfig(BaseModel):
    """Single history layer config"""
    model_config = {"extra": "allow"}
    
    storage: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Storage strategy configs (raw, filtered, etc)"
    )
    memory: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Memory management configs (smart_window, token_budget)"
    )
    filters: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Filter configs (error, duplicate, noise)"
    )
    search: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Search strategy configs (threshold)"
    )
    enable_cache: Optional[bool] = Field(
        default=None,
        description="Enable caching for this tier"
    )
    cache_ttl: Optional[int] = Field(
        default=None,
        description="Cache TTL in seconds"
    )


class HistoryConfig(BaseModel):
    """Multi-tier history config"""
    model_config = {"extra": "allow"}
    
    cache_enabled: bool = Field(
        default=True,
        description="Enable caching for history context"
    )
    
    tier_threshold: int = Field(
        default=50,
        description="Message count threshold to trigger medium-term tier processing"
    )
    
    short_term: Optional[HistoryLayerConfig] = Field(
        default=None,
        description="Short-term history (smart window + token budget)"
    )
    medium_term: Optional[HistoryLayerConfig] = Field(
        default=None,
        description="Medium-term history (filtered storage)"
    )
    long_term: Optional[HistoryLayerConfig] = Field(
        default=None,
        description="Long-term history (semantic search)"
    )
    
    vector: Optional[VectorConfig] = Field(
        default=None,
        description="Vector storage configuration"
    )
    embedding: Optional[EmbeddingConfig] = Field(
        default=None,
        description="Embedding provider configuration"
    )

