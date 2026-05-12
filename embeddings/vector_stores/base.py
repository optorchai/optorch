"""Base vector store interface"""

from abc import ABC, abstractmethod
from typing import List, Optional
from optorch.messaging import Message, MessageContext
from optorch.embeddings.base import BaseEmbeddingProvider


class BaseVectorStore(ABC):
    """Abstract base for vector storage providers"""
    
    def __init__(self, embedding_provider: BaseEmbeddingProvider, **kwargs):
        self.embedding_provider = embedding_provider
    
    @abstractmethod
    async def index_messages(self, messages: List[Message], ctx: MessageContext) -> None:
        """Index messages for vector search"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        messages: List[Message],
        ctx: MessageContext,
        limit: int = 10,
        threshold: float = 0.7
    ) -> Optional[List[Message]]:
        """Search for relevant messages by vector similarity"""
        pass
    
    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        """Clear all vectors for a session"""
        pass
