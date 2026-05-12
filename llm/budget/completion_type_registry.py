"""completion type registry - find budget handlers by name"""
from optorch.llm.budget.completion_types import (
    HardStop,
    FinishSentence,
    FinishParagraph,
    MinimumTokens
)

class CompletionTypeRegistry:
    """find budget handlers by name"""
    
    _types = {
        'hard_stop': HardStop,
        'sentence': FinishSentence,
        'paragraph': FinishParagraph,
        'min_tokens': MinimumTokens,
    }
    
    @classmethod
    def get(cls, type_name: str, **kwargs):
        """get handler instance"""
        if type_name not in cls._types:
            raise ValueError(f"unknown completion type: {type_name}")
        return cls._types[type_name](**kwargs)
    
    @classmethod
    def register(cls, name: str, type_class):
        """add custom type"""
        cls._types[name] = type_class

