"""
History package - conversation memory with caching, storage, and filtering.

Exports core history components for external use.
"""

from .manager import History
from .config import HistoryConfig, VectorConfig, EmbeddingConfig, HistoryLayerConfig
from .sources.session import SessionMessageSource
from .processors import HistoryPersistence, HistoryRetrieval

__all__ = [
    "History",
    "HistoryConfig",
    "HistoryLayerConfig",
    "VectorConfig",
    "EmbeddingConfig",
    "SessionMessageSource",
    "HistoryPersistence",
    "HistoryRetrieval",
]

