from typing import List, Optional, TYPE_CHECKING
import aiohttp
from ..base import BaseEmbeddingProvider

if TYPE_CHECKING:
    from optorch.config.manager import ConfigManager


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama embedding provider - local"""
    
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None, config_manager: Optional['ConfigManager'] = None):
        if base_url is None or model is None:
            if config_manager is None:
                from optorch.config.manager import ConfigManager
                config_manager = ConfigManager()
            
            if base_url is None:
                base_url = config_manager.secret_provider.get("EMBEDDING_BASE_URL") or "http://localhost:11434"
            if model is None:
                model = config_manager.secret_provider.get("EMBEDDING_MODEL") or "nomic-embed-text"
        
        self.base_url: str = base_url.rstrip('/')
        self.model: str = model
        self._dimensions: Optional[int] = None
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        async with aiohttp.ClientSession() as session:
            for text in texts:
                embedding = await self._embed_request(session, text)
                embeddings.append(embedding)
        return embeddings
    
    async def embed_single(self, text: str) -> List[float]:
        async with aiohttp.ClientSession() as session:
            return await self._embed_request(session, text)
    
    async def _embed_request(self, session: aiohttp.ClientSession, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                raise RuntimeError(f"Ollama embedding failed: {response.status}")
            
            data = await response.json()
            embedding = data.get("embedding", [])
            
            if self._dimensions is None:
                self._dimensions = len(embedding)
            
            return embedding
    
    @property
    def dimensions(self) -> int:
        return self._dimensions or 768
