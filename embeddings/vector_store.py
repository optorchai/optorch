from typing import List, Optional, cast, Any
import hashlib
from optorch.logging import get_logger
import chromadb
from chromadb.config import Settings
from optorch.messaging import Message, MessageContext
from .base import BaseEmbeddingProvider

logger = get_logger(__name__)


class VectorStore:
    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        persist_directory: Optional[str] = None
    ):
        self.embedding_provider = embedding_provider
        
        if persist_directory:
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
        else:
            self.client = chromadb.Client(
                settings=Settings(anonymized_telemetry=False)
            )
        
        logger.info(f"Initialized ChromaDB vector store (persist: {persist_directory or 'memory'})")
    
    def _get_collection(self, session_id: str):
        collection_name = f"session_{self._safe_collection_name(session_id)}"
        
        try:
            return self.client.get_collection(name=collection_name)
        except Exception:
            return self.client.create_collection(
                name=collection_name,
                metadata={"session_id": session_id}
            )
    
    def _safe_collection_name(self, session_id: str) -> str:
        return hashlib.md5(session_id.encode()).hexdigest()[:32]
    
    async def index_messages(self, messages: List[Message], ctx: MessageContext) -> None:
        texts = [m.content for m in messages if m.content]
        if not texts:
            return
        
        embeddings = await self.embedding_provider.embed(texts)
        
        collection = self._get_collection(ctx.session_id)
        
        ids = [self._message_hash(msg) for msg in messages if msg.content]
        metadatas = [
            {
                "role": msg.role,
                "timestamp": msg.timestamp.isoformat(),
                "session_id": ctx.session_id
            }
            for msg in messages if msg.content
        ]
        
        collection.upsert(
            ids=ids,
            embeddings=cast(Any, embeddings),
            documents=texts,
            metadatas=cast(Any, metadatas)
        )
        
        logger.info(f"Indexed {len(texts)} messages to ChromaDB for session {ctx.session_id}")
    
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
        
        collection = self._get_collection(ctx.session_id)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results["ids"] or not results["ids"][0]:
            logger.info("ChromaDB search returned no results")
            return None
        
        documents = results.get("documents")
        metadatas = results.get("metadatas")
        distances = results.get("distances")
        
        if not documents or not metadatas or not distances:
            logger.info("ChromaDB search returned incomplete results")
            return None
        
        matched_messages = []
        for doc, metadata, distance in zip(
            documents[0],
            metadatas[0], 
            distances[0]
        ):
            similarity = 1.0 / (1.0 + distance)
            
            if similarity >= threshold:
                for msg in messages:
                    if msg.content == doc:
                        matched_messages.append(msg)
                        break
        
        logger.info(f"ChromaDB search found {len(matched_messages)} messages above threshold {threshold}")
        return matched_messages if matched_messages else None
    
    def _message_hash(self, msg: Message) -> str:
        data = f"{msg.role}:{msg.content}:{msg.timestamp.isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def clear_session(self, session_id: str) -> None:
        collection_name = f"session_{self._safe_collection_name(session_id)}"
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Cleared ChromaDB collection for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to clear collection {collection_name}: {e}")
