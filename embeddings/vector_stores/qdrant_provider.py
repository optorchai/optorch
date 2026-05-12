"""Qdrant vector store provider"""

from typing import List, Optional, TYPE_CHECKING
import hashlib
from optorch.logging import get_logger
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from optorch.messaging import Message, MessageContext
from .base import BaseVectorStore

if TYPE_CHECKING:
    from optorch.config.manager import ConfigManager

logger = get_logger(__name__)


class QdrantVectorStore(BaseVectorStore):
    """Qdrant vector storage - remote or local"""
    
    def __init__(
        self,
        embedding_provider,
        host: Optional[str] = None,
        port: Optional[int] = None,
        collection_name: Optional[str] = None,
        config_manager: Optional['ConfigManager'] = None,
        **kwargs
    ):
        super().__init__(embedding_provider)
        
        if host is None or port is None or collection_name is None:
            if config_manager is None:
                from optorch.config.manager import ConfigManager
                config_manager = ConfigManager()
            
            if host is None:
                host = config_manager.secret_provider.get("VECTOR_HOST") or "localhost"
            if port is None:
                port_str = config_manager.secret_provider.get("VECTOR_PORT") or "6333"
                port = int(port_str)
            if collection_name is None:
                collection_name = config_manager.secret_provider.get("VECTOR_COLLECTION") or "optorch_history"
        
        self.host: str = host
        self.port: int = int(port) if not isinstance(port, int) else port
        self.collection_name: str = collection_name
        
        self.client = QdrantClient(host=self.host, port=self.port)
        self._ensure_collection()
        
        logger.info(f"Qdrant initialized at {self.host}:{self.port} (collection: {self.collection_name})")
    
    def _ensure_collection(self):
        """Create collection if not exists"""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            # Ollama nomic-embed-text is 768 dims, adjust if using different model
            dimensions = getattr(self.embedding_provider, 'dimensions', 768)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE)
            )
            logger.info(f"Created Qdrant collection: {self.collection_name}")
    
    def _point_id(self, msg: Message) -> str:
        """Generate deterministic ID from message content"""
        data = f"{msg.role}:{msg.content}:{msg.timestamp.isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()
    
    async def index_messages(self, messages: List[Message], ctx: MessageContext) -> None:
        texts = [m.content for m in messages if m.content]
        if not texts:
            return
        
        embeddings = await self.embedding_provider.embed(texts)
        
        points = []
        for msg, embedding in zip([m for m in messages if m.content], embeddings):
            points.append(PointStruct(
                id=self._point_id(msg),
                vector=embedding,
                payload={
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "session_id": ctx.session_id
                }
            ))
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        logger.info(f"Indexed {len(points)} messages (session {ctx.session_id})")
    
    async def search(
        self,
        query: str,
        messages: List[Message],
        ctx: MessageContext,
        limit: int = 10,
        threshold: float = 0.7
    ) -> Optional[List[Message]]:
        if not messages:
            return None
        
        query_embedding = await self.embedding_provider.embed_single(query)
        
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            query_filter=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=ctx.session_id))]),
            limit=limit,
            score_threshold=threshold
        ).points
        
        if not results:
            return None
        
        matched_messages = []
        for hit in results:
            if hit.payload:
                content = hit.payload.get("content")
                if content:
                    for msg in messages:
                        if msg.content == content:
                            matched_messages.append(msg)
                            break
        
        logger.info(f"Found {len(matched_messages)} messages above threshold {threshold}")
        return matched_messages if matched_messages else None
    
    def clear_session(self, session_id: str) -> None:
        """Delete all points for a session"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(must=[FieldCondition(key="session_id", match=MatchValue(value=session_id))])
            )
            logger.info(f"Cleared vectors for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to clear session {session_id}: {e}")
