"""no buffering - immediate passthrough"""
from typing import Optional
from optorch.llm.responses.accumulators.base_accumulator import BaseAccumulator

class PassthroughAccumulator(BaseAccumulator):
    """yields chunks immediately without buffering"""
    
    def consume(self, chunk: str) -> Optional[str]:
        return None
    
    def should_passthrough(self) -> bool:
        return True
    
    def flush(self) -> Optional[str]:
        return None
