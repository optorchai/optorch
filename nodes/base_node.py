from abc import ABC, abstractmethod
from typing import Any, List, Optional, Callable, Awaitable, TYPE_CHECKING
from optorch.state import BaseState
from optorch.llm.prompt_manager import PromptManager

if TYPE_CHECKING:
    from optorch.llm.lifecycle.context import LLMContext
    from optorch.llm.lifecycle.hooks import LLMLifecycleHook
    from optorch.controller.node_context import NodeContext


class BaseNode(ABC):
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self._llm_context: Optional['LLMContext'] = None
        self._node_context: Optional['NodeContext'] = None
        self._state: Optional[BaseState] = None
    
    @property
    def state(self) -> BaseState:
        """current execution state"""
        assert self._state is not None, "State not set - call set_state() before accessing"
        return self._state
    
    def set_state(self, state: BaseState) -> None:
        """set execution state"""
        self._state = state
    
    def set_context(self, context: 'NodeContext') -> None:
        """set node context"""
        self._node_context = context
    
    @property
    def controller(self) -> Any:
        """access to NodeController via context"""
        assert self._node_context is not None, "NodeContext not set - only accessible during execute()"
        return self._node_context.controller
    
    @property
    def prompt_manager(self) -> Optional[PromptManager]:
        assert self._node_context is not None, "NodeContext not set - only accessible during execute()"
        return self._node_context.controller._prompt_manager
    
    @property
    def event_emitter(self) -> Any:
        assert self._node_context is not None, "NodeContext not set - only accessible during execute()"
        return self._node_context.events
    
    @property
    def tools(self) -> List[Any]:
        tool_names = self.config.get("tools", [])
        if not tool_names:
            return []
        assert self._node_context is not None, "NodeContext not set - only accessible during execute()"
        return self._node_context.controller.tools.registry().get_tool_schemas(tool_names)
    
    def set_fragment(self, fragment_name: str, value: str) -> None:
        """Set dynamic fragment value before prompt loading
        
        MessageBuilder processor will load prompts with fragments injected.
        Call this in execute() before invoking LLMManager if you need dynamic content.
        """
        if not self.prompt_manager:
            return
        
        fragment = self.prompt_manager.fragment.get(fragment_name)
        if fragment:
            fragment.set_value(value)
    
    def llm_callback(
        self,
        state: BaseState,
        hook: 'LLMLifecycleHook',
        callback: Callable[..., Awaitable[None]]
    ) -> None:
        """Register callback to run at specific LLM lifecycle hook
        
        Callback runs alongside processors for this LLM execution only.
        For global callbacks across all executions, register a processor.
        
        Args:
            state: State with _llm_context - set during PRE_DISPATCH hook
            hook: LLMLifecycleHook (PRE_INVOKE, POST_INVOKE, FINALIZE, etc)
            callback: Async callable(context, *args, **kwargs) to run at hook time
        """
        assert hasattr(state, '_llm_context') and state._llm_context is not None, "No LLMContext in state - ensure PRE_DISPATCH hook ran"
        
        state._llm_context.register_callback(hook, callback)
    
    @abstractmethod
    async def execute(self, state: BaseState) -> BaseState:
        pass
    
    def route(self, state: BaseState) -> str | None:
        return None
    
    async def call(self, node_name: str, state: BaseState) -> BaseState:
        """Call another node and return here when done.
        
        Args:
            node_name: Node to call
            state: Current State object
            
        Returns:
            State object after called node execution
        """
        assert self._node_context is not None, "NodeContext not set - only accessible during execute()"
        state.set("return_to", self.name)
        return await self._node_context.controller.dispatch(node_name, state, self._node_context)
    
    async def tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a registered tool through the registry
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool parameters
            
        Returns:
            Tool execution result
        """
        assert self._node_context is not None, "NodeContext not set - only accessible during execute()"
        return await self._node_context.controller.tools.registry().execute(
            tool_name=tool_name, 
            context=self._node_context,
            **kwargs
        )
    
    async def goto(self, node_name: str, state: BaseState) -> BaseState:
        """Go to another node (does not return to current node).
        
        Use this for mode switching or routing to a different flow.
        Unlike call(), this does not set return_to.
        
        Args:
            node_name: Node to go to
            state: Current State object
            
        Returns:
            State object after target node execution
        """
        assert self._node_context is not None, "NodeContext not set - only accessible during execute()"
        return await self._node_context.controller.dispatch(node_name, state, self._node_context)
