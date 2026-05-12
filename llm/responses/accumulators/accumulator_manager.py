"""factory for creating accumulators based on transformer attributes"""
from optorch.llm.responses.accumulators.base_accumulator import BaseAccumulator
from optorch.llm.responses.accumulators.passthrough_accumulator import PassthroughAccumulator
from optorch.llm.responses.accumulators.pattern_accumulator import PatternAccumulator
from optorch.transformers.base_transformer import BaseTransformer

class AccumulatorManager:
    """create appropriate accumulator for transformer"""
    
    @staticmethod
    def create(transformer: BaseTransformer) -> BaseAccumulator:
        """select accumulator based on transformer class attributes"""
        
        if hasattr(transformer.__class__, 'STREAMING_PATTERNS'):
            patterns = getattr(transformer.__class__, 'STREAMING_PATTERNS')
            return PatternAccumulator(patterns=patterns)
        
        return PassthroughAccumulator()
