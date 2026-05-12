"""
Instance-based node controller
Manages node registry, dispatch, routing, and lifecycle execution.
"""

from typing import Any, Optional, Type, TYPE_CHECKING

from optorch.cache.manager import CacheManager
from optorch.constants import ConfigKeys
from optorch.controller.node_config import NodeConfig
from optorch.controller.helpers import (
    NodeRegistryHelper,
    IntentRegistryHelper,
    ToolRegistryHelper,
    TransformerRegistryHelper,
    RetryHelper,
    LLMHelper,
    HistoryHelper,
    CacheHelper,
)
from optorch.events.decorators import emits
from optorch.events.event_types import EventTypes
from optorch.history.manager import History
from optorch.intents.intent_registry import IntentRegistry
from optorch.lifecycle.lifecycle_executor import LifecycleExecutor
from optorch.llm.llm_registry import LLMRegistry
from optorch.llm.prompt_manager import PromptManager
from optorch.nodes.base_node import BaseNode
from optorch.registry import Registry
from optorch.retry import RetryHandler
from optorch.routing.route_resolver import RouteResolver
from optorch.routing.routing_context import RoutingContext
from optorch.state import BaseState
from optorch.tools.tool_registry import ToolRegistry
from optorch.transformers.transformer_registry import TransformerRegistry

if TYPE_CHECKING:
    from optorch.controller.node_context import NodeContext


# module-level instance for node property access
_instance: Optional['NodeController'] = None


class NodeController:
    """Instance-based controller managing nodes, intents, tools, and dispatch."""
    
    def __init__(
        self,
        intent_registry: Optional[IntentRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
        transformer_registry: Optional[TransformerRegistry] = None,
        llm_registry: Optional[LLMRegistry] = None,
        lifecycle_executor: Optional[LifecycleExecutor] = None,
        history: Optional[History] = None,
        cache_manager: Optional[CacheManager] = None,
        prompt_manager: Optional[PromptManager] = None,
    ):
        global _instance
        _instance = self
        
        if intent_registry is None:
            intent_registry = IntentRegistry()
        if tool_registry is None:
            tool_registry = ToolRegistry()
        if transformer_registry is None:
            transformer_registry = TransformerRegistry()
        if llm_registry is None:
            llm_registry = LLMRegistry()
        if lifecycle_executor is None:
            lifecycle_executor = LifecycleExecutor(intent_registry)
        
        self._node_registry = Registry[Type[Any]]()
        self._node_configs = Registry[NodeConfig]()
        self._node_instances = Registry[Any]()
        
        self._intent_registry = intent_registry
        self._tool_registry = tool_registry
        self._transformer_registry = transformer_registry
        self._llm_registry = llm_registry
        self._lifecycle_executor = lifecycle_executor
        
        self._history = history
        self._cache_manager = cache_manager
        self._prompt_manager = prompt_manager or PromptManager()
        self.nodes = NodeRegistryHelper(self)
        self.intents = IntentRegistryHelper(self)
        self.tools = ToolRegistryHelper(self)
        self.transformers = TransformerRegistryHelper(self)
        self.retry = RetryHelper(self)
        self.llm = LLMHelper(self)
        self.history = HistoryHelper(self)
        self.cache = CacheHelper(self)
    
    @classmethod
    def from_config(
        cls,
        intent_registry: Optional[IntentRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
        transformer_registry: Optional[TransformerRegistry] = None,
        llm_registry: Optional[LLMRegistry] = None,
        lifecycle_executor: Optional[LifecycleExecutor] = None,
        history: Optional[History] = None,
        cache_manager: Optional[CacheManager] = None,
        prompt_manager: Optional[PromptManager] = None,
    ) -> 'NodeController':
        """Factory method creating controller from config"""
        return cls(
            intent_registry=intent_registry,
            tool_registry=tool_registry,
            transformer_registry=transformer_registry,
            llm_registry=llm_registry,
            lifecycle_executor=lifecycle_executor,
            history=history,
            cache_manager=cache_manager,
            prompt_manager=prompt_manager,
        )
    
    @property
    def prompt_manager(self) -> PromptManager:
        return self._prompt_manager
    
    @prompt_manager.setter
    def prompt_manager(self, value: PromptManager) -> None:
        self._prompt_manager = value
    
    @classmethod
    def get_instance(cls) -> 'NodeController':
        """Get current instance - for node property access"""
        if _instance is None:
            raise RuntimeError("NodeController not initialized")
        return _instance
    
    @emits(EventTypes.NODE)
    async def dispatch(self, node_name: str, state: BaseState, context: Optional['NodeContext'] = None) -> BaseState:
        """
        Dispatch to node with lifecycle execution and routing.
        
        Args:
            node_name: Node to dispatch to
            state: Current state
            context: Optional NodeContext for dependency injection
        """
        node = self._get_or_create_node(node_name)
        node.set_state(state)
        if context:
            node.set_context(context)
        
        from optorch.constants import StateKeys
        state[StateKeys.CURRENT_NODE] = node_name
        
        node_config = self._node_configs.get(node_name) if self._node_configs.has(node_name) else NodeConfig()
        if node_config.phase:
            state[StateKeys.CURRENT_PHASE] = node_config.phase
        
        routing_context = RoutingContext(current_node=node_name, result=state)
        
        result = await RetryHandler.execute_with_retry(
            node, 
            state, 
            lambda n, s: self._execute_lifecycle(n, s, context), 
            node_config.model_dump()
        )
        
        routing_context.result = result
        routing_context.add_to_history(node_name)
        
        next_node = self._resolve_next_node(node_name, routing_context)
        
        if "_retry_fallback" in result:
            next_node = result.get("_retry_fallback")
            result.pop("_retry_fallback", None)  # use pop instead of del for BaseState compatibility
        
        if next_node:
            return await self.dispatch(next_node, result, context)
        
        return result
    
    def _get_or_create_node(self, node_name: str) -> BaseNode:
        """Get cached node instance or create new one"""
        if not self._node_instances.has(node_name):
            node_class = self._node_registry.get(node_name)
            node_config = self._node_configs.get(node_name) if self._node_configs.has(node_name) else NodeConfig()
            
            node_instance = node_class(name=node_name, config=node_config.model_dump())
            self._node_instances.register(node_name, node_instance)
        
        return self._node_instances.get(node_name)
    
    async def _execute_lifecycle(self, node: BaseNode, state: BaseState, context: Optional['NodeContext'] = None) -> BaseState:
        """Execute node through lifecycle hooks"""
        return await self._lifecycle_executor.execute_with_node(node, state, context)
    
    def _resolve_next_node(self, node_name: str, context: RoutingContext) -> Optional[str]:
        """Resolve next node via lifecycle routing or config"""
        from optorch.constants import StateKeys
        if StateKeys.NEXT_NODE in context.result:
            lifecycle_route = context.result[StateKeys.NEXT_NODE]
            if lifecycle_route:
                return lifecycle_route
        
        if not self._node_configs.has(node_name):
            return None
        
        node_config = self._node_configs.get(node_name)
        routing_config = node_config.routing.model_dump(exclude_none=True) if node_config.routing else {}
        
        return RouteResolver.resolve(routing_config, context)
    
    def clear_instances(self) -> None:
        """Clear cached node instances (useful for testing)"""
        self._node_instances.clear()
