"""base completion type for budget control"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Tuple


class BaseCompletionType(ABC):
    """abstract completion type for controlling stream termination"""
    
    def __init__(self, **config):
        self.config = config
    
    @abstractmethod
    def should_stop(self, cost: Decimal, budget: Decimal, tokens: int) -> bool:
        """decide if streaming should stop based on cost/budget/tokens"""
        pass
    
    @abstractmethod
    def should_yield(self, chunk: str, buffer: str) -> Tuple[bool, str]:
        """
        decide if chunk should be yielded or buffered
        returns (should_yield, updated_buffer)
        """
        pass
    
    @abstractmethod
    def finalize(self, buffer: str) -> str:
        """flush remaining buffer on completion"""
        pass
