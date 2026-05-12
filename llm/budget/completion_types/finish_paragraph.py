"""finish paragraph - complete paragraph before stopping"""
from decimal import Decimal
from typing import Tuple
from optorch.llm.budget.completion_types.base_completion_type import BaseCompletionType


class FinishParagraph(BaseCompletionType):
    """buffer chunks until paragraph boundary"""
    
    def __init__(self, **config):
        super().__init__(**config)
        self._over_budget = False
    
    def should_stop(self, cost: Decimal, budget: Decimal, tokens: int) -> bool:
        if cost >= budget:
            self._over_budget = True
        return False
    
    def should_yield(self, chunk: str, buffer: str) -> Tuple[bool, str]:
        new_buffer = buffer + chunk
        
        if not self._over_budget:
            return True, ""
        
        if "\n\n" in new_buffer:
            return True, ""
        
        return False, new_buffer
    
    def finalize(self, buffer: str) -> str:
        return buffer
