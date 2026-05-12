from dataclasses import dataclass
from typing import Optional


@dataclass
class EmbeddingConfig:
    provider: str = "openai"
    model: Optional[str] = None
    dimensions: Optional[int] = None
    batch_size: Optional[int] = None
