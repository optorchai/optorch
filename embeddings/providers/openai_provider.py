from typing import List, Optional
from ..base import BaseEmbeddingProvider
from ..constants import DEFAULT_VECTOR_DIM


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider"""
    
    def __init__(self, model: str = "text-embedding-3-small", dimensions: Optional[int] = None):
        self.model = model
        self._dimensions = dimensions or DEFAULT_VECTOR_DIM
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI()
        return self._client
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [item.embedding for item in response.data]
    
    async def embed_single(self, text: str) -> List[float]:
        embeddings = await self.embed([text])
        return embeddings[0]
    
    @property
    def dimensions(self) -> int:
        return self._dimensions
