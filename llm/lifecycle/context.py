"""LLM Context - Carries state through LLM lifecycle"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Awaitable, Dict, List, Optional, Set, TYPE_CHECKING
from collections import defaultdict
import asyncio

from optorch.state.base_state import BaseState
from optorch.llm.lifecycle.hooks import LLMLifecycleHook

if TYPE_CHECKING:
    from optorch.llm.base_client import BaseLLMClient
    from optorch.llm.responses import LLMResponse
    from optorch.events.event_emitter import EventEmitter
    from optorch.controller.node_context import NodeContext


@dataclass
class LLMContext:
    """Carries state through LLM lifecycle - MUTATED IN-PLACE by processors"""
    
    # Core (immutable after creation)
    client: Optional['BaseLLMClient']  # can be None for partial contexts
    messages: List[Dict[str, Any]]  # Mutated by processors (history injection, tool results)
    config: Dict[str, Any]  # tools, transformers, history, budget, temperature, etc.
    events: 'EventEmitter'  # event emitter instance from container
    node_context: Optional['NodeContext'] = None  # NodeContext - for accessing registries
    
    # State (mutated during lifecycle)
    state: Optional[BaseState] = None  # State or StreamingState - carries workflow state
    response: Optional["LLMResponse"] = None  # LLMResponse - set during INVOKE phase
    
    # Budget tracking
    budget: Optional[Decimal] = None  # Resolved from hierarchy: invoke > node > phase > global
    budget_consumed: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Substates (controls which processors run)
    active_substates: Set[str] = field(default_factory=lambda: {"default"})
    
    # Metadata (mutated by processors)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Response metadata
    processor_data: Dict[str, Any] = field(default_factory=dict)  # Inter-processor state
    
    # Execution control
    skip_remaining: bool = False  # Allow processors to short-circuit
    streaming: bool = False  # Set by executor based on invoke/astream
    user_callbacks: Dict[LLMLifecycleHook, List[tuple]] = field(default_factory=lambda: defaultdict(list))
    _current_phase: Optional[LLMLifecycleHook] = None  # Current lifecycle phase (set by executor)
    _pending_tasks: List[asyncio.Task] = field(default_factory=list)  # Background tasks spawned by processors
    
    def register_callback(self, hook: LLMLifecycleHook, callback: Callable[..., Awaitable[None]], *args, **kwargs) -> None:
        """Register user callback to run at specific lifecycle hook - runs alongside processors
        
        Args:
            hook: Lifecycle hook to register for
            callback: Async callable - will receive (context, *args, **kwargs)
            *args: Additional positional args to pass to callback
            **kwargs: Additional keyword args to pass to callback
        """
        self.user_callbacks[hook].append((callback, args, kwargs))
    
    def register_pending_task(self, task: asyncio.Task, name: str = "unnamed") -> None:
        """Register background task spawned by processor - allows tracking async work
        
        Args:
            task: Asyncio task
            name: Name for logging
        """
        self._pending_tasks.append(task)
    
    async def wait_for_pending_tasks(self, timeout: float = 5.0) -> None:
        """Wait for all pending background tasks to complete
        
        Args:
            timeout: Max time to wait in seconds
        """
        if not self._pending_tasks:
            return
        
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._pending_tasks, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            from optorch.logging import get_logger
            logger = get_logger(__name__)
            logger.warning(f"Pending tasks timed out after {timeout}s")
        
        self._pending_tasks.clear()
