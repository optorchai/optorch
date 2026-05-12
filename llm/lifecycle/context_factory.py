"""LLM Context Factory - Creates contexts with plugins"""

from typing import Dict, Optional, Any, List, Callable, Tuple, TYPE_CHECKING
from decimal import Decimal

from optorch.llm.lifecycle.context import LLMContext
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.state.base_state import BaseState

if TYPE_CHECKING:
    from optorch.events.event_emitter import EventEmitter
    from optorch.llm.base_client import BaseLLMClient
    from optorch.controller.node_context import NodeContext


class _Registration:
    """Nested class for registration namespacing"""
    
    def __init__(self, factory_class):
        self._factory = factory_class
    
    def plugin(self, enricher: Callable[[LLMContext], None]) -> None:
        """Register plugin enricher
        
        Args:
            enricher: Callback that receives LLMContext and enriches it
        """
        if enricher not in self._factory._plugins:
            self._factory._plugins.append(enricher)
    
    def user_callback(self, hook: LLMLifecycleHook, callback: Callable, tag: str, *args, **kwargs) -> None:
        """Register user callback for lifecycle hook
        
        Args:
            hook: Lifecycle hook to register for
            callback: Async callable to execute at hook
            tag: Identifier for this callback (for cleanup)
            *args: Args to pass to callback
            **kwargs: Kwargs to pass to callback
        """
        self._factory._user_callbacks.append((tag, hook, callback, args, kwargs))


class _Clear:
    """Nested class for clear operations"""
    
    def __init__(self, factory_class):
        self._factory = factory_class
    
    def user_callback(self, tag: str) -> None:
        """Clear user callbacks by tag
        
        Args:
            tag: Only remove callbacks with this tag
        """
        self._factory._user_callbacks[:] = [
            cb for cb in self._factory._user_callbacks if cb[0] != tag
        ]


class LLMContextFactory:
    """Factory for creating LLMContext instances
    
    supports plugin enrichers - callbacks that attach metadata
    enrichers decouple factory from specific concerns (budget, cache, etc)
    """
    
    _plugins: List[Callable[[LLMContext], None]] = []
    _user_callbacks: List[Tuple[str, LLMLifecycleHook, Callable, tuple, dict]] = []
    
    register = _Registration(None)
    clear = _Clear(None)
    
    @classmethod
    def _apply_plugins(cls, context: LLMContext) -> None:
        """apply all registered plugins to context"""
        for enricher in cls._plugins:
            enricher(context)
    
    @classmethod
    def _apply_user_callbacks(cls, context: LLMContext) -> None:
        """apply registered user callbacks to context"""
        for tag, hook, callback, args, kwargs in cls._user_callbacks:
            context.register_callback(hook, callback, *args, **kwargs)
    
    @classmethod
    def create(
        cls,
        events: 'EventEmitter',
        client: Optional['BaseLLMClient'] = None,
        messages: Optional[list] = None,
        config: Optional[Dict[str, Any]] = None,
        state: Optional[BaseState] = None,
        budget: Optional[Decimal] = None,
        streaming: bool = False,
        node_context: Optional['NodeContext'] = None
    ) -> LLMContext:
        """Create LLMContext
        
        Args:
            events: EventEmitter instance from container
            client: BaseLLMClient instance (None for partial context)
            messages: Message history (empty list for partial context)
            config: Configuration dict
            state: State for history/entity access
            budget: Resolved budget
            streaming: Whether this will be streaming
            node_context: NodeContext for accessing registries
            
        Returns:
            LLMContext instance
        """
        context = LLMContext(
            client=client,
            messages=messages or [],
            config=config or {},
            events=events,
            state=state,
            budget=budget,
            streaming=streaming,
            node_context=node_context
        )
        
        cls._apply_plugins(context)
        cls._apply_user_callbacks(context)
        return context
    
    @classmethod
    def populate(
        cls,
        context: Optional[LLMContext],
        events: 'EventEmitter',
        client: 'BaseLLMClient',
        messages: list,
        config: Dict[str, Any],
        state: Optional[BaseState] = None,
        budget: Optional[Decimal] = None,
        streaming: bool = False,
        node_context: Optional['NodeContext'] = None
    ) -> LLMContext:
        """Create new context or populate existing with required fields
        
        Args:
            context: Existing context or None
            events: EventEmitter instance from container
            client: BaseLLMClient instance
            messages: Message history
            config: Configuration dict
            state: State for history/entity access
            budget: Resolved budget
            streaming: Whether this will be streaming
            node_context: NodeContext for accessing registries
            
        Returns:
            Populated LLMContext
        """
        if context is None:
            return cls.create(
                events=events,
                client=client,
                messages=messages,
                config=config,
                state=state,
                budget=budget,
                streaming=streaming,
                node_context=node_context
            )
        
        # populate existing context fields
        context.client = client
        context.messages = messages
        context.config = {**context.config, **config}
        context.state = state or context.state
        context.budget = budget or context.budget
        context.streaming = streaming
        context.node_context = node_context or context.node_context
        
        return context


# Initialize register namespace with factory class
LLMContextFactory.register = _Registration(LLMContextFactory)
LLMContextFactory.clear = _Clear(LLMContextFactory)
