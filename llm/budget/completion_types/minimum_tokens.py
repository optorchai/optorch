"""minimum tokens - guarantee minimum output even if over budget"""
from decimal import Decimal
from typing import Tuple
from optorch.llm.budget.completion_types.base_completion_type import BaseCompletionType


class MinimumTokens(BaseCompletionType):
    """guarantee minimum tokens regardless of budget"""
    
    def __init__(self, min_tokens: int = 50, **config):
        super().__init__(**config)
        self.min_tokens = min_tokens
    
    def should_stop(self, cost: Decimal, budget: Decimal, tokens: int) -> bool:
        if tokens < self.min_tokens:
            return False
        
        return cost >= budget
    
    def should_yield(self, chunk: str, buffer: str) -> Tuple[bool, str]:
        return True, buffer
    
    def finalize(self, buffer: str) -> str:
        return ""
