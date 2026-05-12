"""hard stop - immediate halt when budget exceeded"""
from decimal import Decimal
from typing import Tuple
from optorch.llm.budget.completion_types.base_completion_type import BaseCompletionType


class HardStop(BaseCompletionType):
    """stop immediately when budget exceeded"""
    
    def should_stop(self, cost: Decimal, budget: Decimal, tokens: int) -> bool:
        return cost >= budget
    
    def should_yield(self, chunk: str, buffer: str) -> Tuple[bool, str]:
        return True, buffer
    
    def finalize(self, buffer: str) -> str:
        return ""
