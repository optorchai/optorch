"""qdrant prompt provider - semantic search from vector store"""

from optorch.llm.prompts import PromptProvider
from typing import Any, Optional, TYPE_CHECKING
from optorch.logging import get_logger
import os

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

logger = get_logger(__name__)


class QdrantPromptProvider(PromptProvider):
    """load prompts from qdrant vector store using semantic search"""
    
    def __init__(self, qdrant_url: str, collection: str) -> None:
        self._qdrant_url = qdrant_url
        self._collection = collection
        self._qdrant: Optional['QdrantClient'] = None
        logger.debug("qdrant prompt provider initialized")
    
    def _get_qdrant(self) -> Optional['QdrantClient']:
        """lazy qdrant client initialization"""
        if self._qdrant is None:
            try:
                from qdrant_client import QdrantClient
                self._qdrant = QdrantClient(url=self._qdrant_url)
                logger.info(f"connected to qdrant: {self._qdrant_url}")
            except ImportError:
                logger.warning("qdrant-client package not installed - pip install qdrant-client")
                self._qdrant = None
                return None
            except Exception as e:
                logger.warning(f"failed to connect to qdrant: {e}")
                self._qdrant = None
                return None
        return self._qdrant
    
    async def load(self, prompt_name: str, fragments: dict[str, Any]) -> str | None:
        """load prompt from qdrant by exact name match"""
        client = self._get_qdrant()
        if not client:
            return None
        
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            
            # exact name lookup using scroll with filter
            results = client.scroll(
                collection_name=self._collection,
                scroll_filter=Filter(
                    must=[FieldCondition(key="name", match=MatchValue(value=prompt_name))]
                ),
                limit=1
            )
            
            if results and results[0]:
                point = results[0][0]
                if point.payload and isinstance(point.payload, dict):
                    template = point.payload.get('template')
                    if not template or not isinstance(template, str):
                        return None
                    
                    # fragment injection
                    for key, value in fragments.items():
                        template = template.replace(f"{{{key}}}", value if value else "")
                    
                    logger.info(f"loaded '{prompt_name}' from qdrant")
                    return template
            
            return None
        except Exception as e:
            logger.error(f"qdrant load failed for '{prompt_name}': {e}")
            return None
    
    @property
    def name(self) -> str:
        return "Qdrant"
