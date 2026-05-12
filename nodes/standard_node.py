from typing import Any, Callable
from optorch.logging import get_logger

from optorch.events.listeners.base import BaseListener
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.nodes.base_node import BaseNode
from optorch.state import BaseState, StateFactory
from optorch.state.streaming_state import StreamingState

logger = get_logger(__name__)

class StandardNode(BaseNode):
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from LLM response"""
        if hasattr(self, 'response') and hasattr(self.response, 'metadata') and self.response.metadata:
            return self.response.metadata.get(key, default)
        return default
    
    async def execute(self, state: BaseState) -> BaseState:
        """Execute node - lifecycle handles everything
        
        Supports streaming when state is StreamingState or streaming=True in config
        """
        llm_name = self.config.get("llm", "default")
        
        streaming = (
            isinstance(state, StreamingState) or 
            self.config.get("streaming", False) or 
            state.get("_streaming", False)
        )
        
        if not self._node_context or not self._node_context.container.llm_manager:
            raise RuntimeError("LLMManager not available in NodeContext")
        
        manager = self._node_context.container.llm_manager
        
        config = {
            "prompts": self.config.get("prompts", {}),
            "transformers": self.config.get("transformers", []),
            "budget": self.config.get("budget"),
            "node_name": self.name,
            "prompt_manager": self.prompt_manager
        }
        
        if streaming:
            response = await manager.astream(
                model=llm_name,
                messages=[],
                tools=self.tools if self.config.get("tools") else None,
                state=state,
                config=config,
                event_emitter=self.event_emitter,
                node_context=self._node_context,
                context=state._llm_context if hasattr(state, '_llm_context') else None
            )
            return StateFactory.make_streaming(state, response.stream)
        else:
            response = await manager.invoke(
                model=llm_name,
                messages=[],
                tools=self.tools if self.config.get("tools") else None,
                state=state,
                config=config,
                event_emitter=self.event_emitter,
                node_context=self._node_context,
                context=state._llm_context if hasattr(state, '_llm_context') else None
            )
            
            self.response = response
            state.set("response", response.content)
            
            return state
        
    def listener(self, listener_class: type, callback: Callable, *args, **kwargs) -> BaseListener:
        """Register event listener with auto-cleanup at FINALIZE
        
        Args:
            listener_class: Listener class to instantiate
            callback: Callback function(event, state, *args, **kwargs)
            *args: Additional positional arguments forwarded to callback
            **kwargs: Additional keyword arguments forwarded to callback
            
        Returns:
            Listener instance
        """
        listener = listener_class(lambda event: callback(event, self.state, *args, **kwargs))
        self.event_emitter.register_listener(listener)
        self.llm_callback(self.state, LLMLifecycleHook.FINALIZE, listener.cleanup)
        return listener