"""abstract base for stream accumulators"""
from abc import ABC, abstractmethod
from typing import Optional

class BaseAccumulator(ABC):
    """buffer stream chunks based on strategy"""
    
    @abstractmethod
    def consume(self, chunk: str) -> Optional[str]:
        """consume chunk, return accumulated content when ready (or None to keep buffering)"""
        pass
    
    @abstractmethod
    def should_passthrough(self) -> bool:
        """whether to yield chunk immediately (for non-buffered content)"""
        pass
    
    @abstractmethod
    def flush(self) -> Optional[str]:
        """return any remaining buffered content"""
        pass
