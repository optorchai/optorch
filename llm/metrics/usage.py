"""Token usage tracking"""
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Usage:
    """Token counts and cost"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    currency: str = "usd"
    
    @classmethod
    def create(cls, model: str, input_tokens: int, output_tokens: int, currency: str = "usd") -> "Usage":
        """Build usage with cost calculated"""
        from optorch.llm.pricing import Pricing
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=Pricing.calculate_cost(model, input_tokens, output_tokens),
            currency=currency
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """For serialization"""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.input_tokens,
            "completion_tokens": self.output_tokens,
            "cost": self.cost,
            "currency": self.currency
        }
