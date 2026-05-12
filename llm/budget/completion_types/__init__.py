"""completion type implementations"""
from optorch.llm.budget.completion_types.base_completion_type import BaseCompletionType
from optorch.llm.budget.completion_types.hard_stop import HardStop
from optorch.llm.budget.completion_types.finish_sentence import FinishSentence
from optorch.llm.budget.completion_types.finish_paragraph import FinishParagraph
from optorch.llm.budget.completion_types.minimum_tokens import MinimumTokens

__all__ = ["BaseCompletionType", "HardStop", "FinishSentence", "FinishParagraph", "MinimumTokens"]
