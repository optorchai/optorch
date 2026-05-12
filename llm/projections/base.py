"""base cost projector interface"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Dict, Any


class BaseCostProjector(ABC):
    """abstract cost projector"""
    
    def __init__(self, config: dict | None = None):
        """init with optional config for output estimation"""
        self._config = config or {}
    
    @abstractmethod
    def estimate_input(self, messages: List[Dict[str, Any]]) -> int:
        """estimate input size from messages"""
        pass
    
    @abstractmethod
    def estimate_output(self, model: str) -> int:
        """estimate output size from config or model defaults"""
        pass
    
    @abstractmethod
    def calculate_cost(
        self, 
        model: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> Decimal:
        """calculate total cost"""
        pass
    
    def predict_cost(self, model: str, messages: List[Dict[str, Any]]) -> Decimal:
        """convenience - predict total cost from messages"""
        input_tokens = self.estimate_input(messages)
        output_tokens = self.estimate_output(model)
        return self.calculate_cost(model, input_tokens, output_tokens)
