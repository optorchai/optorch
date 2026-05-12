"""Base lifecycle executor - generic pattern for hook-based execution"""
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, TYPE_CHECKING

from optorch.events.decorators import emits
from optorch.events.event_types import EventTypes

if TYPE_CHECKING:
    from optorch.controller.node_context import NodeContext

THook = TypeVar('THook')
TContext = TypeVar('TContext')


class BaseLifecycleExecutor(ABC, Generic[THook, TContext]):
    """Generic lifecycle executor pattern
    
    Subclasses define:
    - Hook types (enum)
    - Context type (data container)
    - Hook execution logic
    """
    
    @abstractmethod
    def get_hooks(self) -> List[THook]:
        """ordered list of hooks to execute"""
        pass
    
    @abstractmethod
    async def execute_hook(self, hook: THook, context: TContext) -> TContext:
        """execute single hook, return modified context"""
        pass
    
    def should_skip(self, context: TContext) -> bool:
        """override to short-circuit execution"""
        return False
    
    @emits(EventTypes.LIFECYCLE)
    async def execute(self, context: TContext, node_context: Optional['NodeContext'] = None) -> TContext:
        """run through all hooks in order"""
        for hook in self.get_hooks():
            if self.should_skip(context):
                break
            
            context = await self.execute_hook(hook, context)
        
        return context
