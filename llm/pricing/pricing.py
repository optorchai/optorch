"""LLM pricing utilities for cost tracking"""
from optorch.logging import get_logger
from decimal import Decimal
from typing import Optional

from .models import CostsConfig

logger = get_logger(__name__)

DEFAULT_CURRENCY = 'USD'


class Pricing:
    """Unified pricing for session totals and streaming budget control - no file I/O"""
    _config: Optional[CostsConfig] = None
    
    @classmethod
    def initialize(cls, config: Optional[CostsConfig] = None):
        """init with CostsConfig model - defaults if not provided"""
        cls._config = config or CostsConfig()
        logger.debug(f"initialized pricing with {len(cls._config.pricing)} models ({cls._config.currency})")
    
    @classmethod
    def _get_config(cls) -> CostsConfig:
        """lazy init with defaults if not explicitly initialized"""
        if cls._config is None:
            cls._config = CostsConfig()
        return cls._config
    
    @classmethod
    def calculate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> float:
        """calculate cost for session totals/metrics"""
        config = cls._get_config()
        pricing = config.pricing.get(model)
        if not pricing:
            return 0.0
        cost = (input_tokens / 1_000_000 * pricing.input) + (output_tokens / 1_000_000 * pricing.output)
        return round(cost, 6)
    
    @classmethod
    def cost_per_chunk(cls, model: str, tokens: int, is_completion: bool = True) -> Decimal:
        """calculate cost for streaming budget control - decimal precision"""
        config = cls._get_config()
        pricing = config.pricing.get(model)
        if not pricing:
            return Decimal("0")
        
        rate = pricing.output if is_completion else pricing.input
        return (Decimal(tokens) / Decimal("1000000")) * Decimal(str(rate))
    
    @classmethod
    def total_cost(cls, model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
        """calculate total as decimal for budget comparisons"""
        prompt_cost = cls.cost_per_chunk(model, prompt_tokens, is_completion=False)
        completion_cost = cls.cost_per_chunk(model, completion_tokens, is_completion=True)
        return prompt_cost + completion_cost
    
    @classmethod
    def get_currency(cls) -> str:
        config = cls._get_config()
        return config.currency
