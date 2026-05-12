"""Base Processor - Abstract interface for lifecycle processors"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set

from .hooks import LLMLifecycleHook
from .context import LLMContext


class BaseLLMProcessor(ABC):
    """Abstract base for all lifecycle processors - similar to intent hook pattern"""
    
    def __init__(self):
        self.substates: Optional[Set[str]] = None
        self.exclude_substates: Optional[Set[str]] = None
        self.order: int = 100
    
    @property
    @abstractmethod
    def hook(self) -> LLMLifecycleHook:
        """Which lifecycle phase this processor runs in"""
        pass
    
    @abstractmethod
    async def process(self, context: LLMContext) -> None:
        """Process context in-place - mutate context.messages, context.response, etc."""
        pass
    
    def should_run(self, context: LLMContext) -> bool:
        """Check if processor should run based on context.skip_remaining and substates"""
        if context.skip_remaining:
            return False
        
        return self.matches_substates(context.active_substates)
    
    def matches_substates(self, active_substates: Set[str]) -> bool:
        """Check if processor matches active substates"""
        if self.exclude_substates:
            if active_substates & self.exclude_substates:
                return False
        
        if self.substates:
            return bool(active_substates & self.substates)
        
        return True
