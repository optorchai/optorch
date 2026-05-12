"""Lifecycle executor with configurable hooks."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from optorch.constants import ConfigKeys, StateKeys
from optorch.events.decorators import emits
from optorch.events.event_types import EventTypes
from optorch.intents.intent_context import IntentContext
from optorch.intents.intent_registry import IntentRegistry
from optorch.lifecycle.base_executor import BaseLifecycleExecutor
from optorch.lifecycle.hooks import LifecycleHook
from optorch.nodes.base_node import BaseNode
from optorch.state import BaseState

if TYPE_CHECKING:
    from optorch.controller.node_context import NodeContext

@dataclass
class NodeLifecycleContext:
    """context for node lifecycle execution"""
    node: BaseNode
    state: BaseState
    skip_execution: bool = False


@dataclass
class HookConfig:
    """single lifecycle hook configuration"""
    hook: LifecycleHook
    enabled: bool = True
    execute_intents: bool = False  # whether to execute intents for this hook
    node_method: Optional[str] = None  # optional node method to call
    core_intents: Optional[List[str]] = None  # core intents from optorch config
    
    def __post_init__(self):
        if self.core_intents is None:
            self.core_intents = []


class LifecycleExecutor(BaseLifecycleExecutor[LifecycleHook, NodeLifecycleContext]):
    """
    lifecycle executor with configurable hooks.
    """
    
    def __init__(
        self,
        intent_registry: IntentRegistry,
        hooks_config: Optional[List[Dict[str, Any]]] = None
    ):
        self.intent_registry = intent_registry
        self._hooks_config = self._build_hooks_config(hooks_config or [])
    
    @classmethod
    def from_config(
        cls,
        config: Dict[str, Any],
        intent_registry: IntentRegistry
    ) -> 'LifecycleExecutor':
        """Factory method creating executor from optorch config"""
        hooks_config = config.get('lifecycle', {}).get('hooks', [])
        return cls(intent_registry, hooks_config)
    
    def _build_hooks_config(self, hooks_config: List[Dict[str, Any]]) -> List[HookConfig]:
        """Build hook configs with defaults if empty"""
        if not hooks_config:
            # default hook sequence if no config
            return [
                HookConfig(
                    hook=LifecycleHook.PRE_DISPATCH,
                    execute_intents=True,
                    core_intents=["create_llm_context"]
                ),
                HookConfig(hook=LifecycleHook.EXECUTE, node_method='execute'),
                HookConfig(
                    hook=LifecycleHook.POST_DISPATCH,
                    execute_intents=True,
                    core_intents=["cleanup_llm_context"]
                ),
                HookConfig(hook=LifecycleHook.ROUTE, node_method='route'),
            ]
        
        result = []
        for hook_spec in hooks_config:
            hook = LifecycleHook[hook_spec['name'].upper()]
            result.append(HookConfig(
                hook=hook,
                enabled=hook_spec.get('enabled', True),
                execute_intents=hook_spec.get('execute_intents', False),
                node_method=hook_spec.get('node_method'),
                core_intents=hook_spec.get('core_intents', []),
            ))
        return result
    
    def get_hooks(self) -> List[LifecycleHook]:
        """ordered hooks from config"""
        return [hc.hook for hc in self._hooks_config if hc.enabled]
    
    async def execute_hook(
        self,
        hook: LifecycleHook,
        context: NodeLifecycleContext
    ) -> NodeLifecycleContext:
        """
        execute single hook via config-driven dispatch.
        
        replaces hardcoded if/elif with iterator pattern.
        """
        hook_config = self._get_hook_config(hook)
        if not hook_config or not hook_config.enabled:
            return context
        
        node = context.node
        state = context.state
        
        if hook_config.execute_intents:
            state, skip_exec = await self._execute_intents(
                node, state, hook
            )
            if hook == LifecycleHook.PRE_DISPATCH:
                context.skip_execution = skip_exec
        
        if hook_config.node_method:
            state = await self._call_node_method(node, state, hook_config.node_method, context)
        
        context.state = state
        return context
    
    @emits(EventTypes.LIFECYCLE)
    async def execute_with_node(self, node: BaseNode, state: BaseState, context: Optional['NodeContext'] = None) -> BaseState:
        """execute lifecycle for a specific node"""
        lifecycle_context = NodeLifecycleContext(node=node, state=state)
        result_context = await self.execute(lifecycle_context, context)
        return result_context.state
    
    def _get_hook_config(self, hook: LifecycleHook) -> Optional[HookConfig]:
        """get config for specific hook"""
        for hc in self._hooks_config:
            if hc.hook == hook:
                return hc
        return None
    
    async def _execute_intents(
        self,
        node: BaseNode,
        state: BaseState,
        hook: LifecycleHook
    ) -> tuple[BaseState, bool]:
        """execute intents for hooks"""
        config_key = (
            ConfigKeys.PRE_DISPATCH if hook == LifecycleHook.PRE_DISPATCH
            else ConfigKeys.POST_DISPATCH
        )
        
        hook_config = self._get_hook_config(hook)
        core_intents = hook_config.core_intents if hook_config else []        
        node_intents = node.config.get(ConfigKeys.INTENTS, {}).get(config_key, [])
        all_intents = core_intents + node_intents
        
        if not all_intents:
            return state, False
        
        context = IntentContext(node=node, operation=hook.value, data=state)
        results = await self.intent_registry.execute_multiple(all_intents, context)
        
        # intent can override state
        if context.result is not None:
            state = context.result
        else:
            for result in results.values():
                if isinstance(result, BaseState):
                    state = result
        
        return state, context.skip_execution
    
    async def _call_node_method(
        self,
        node: BaseNode,
        state: BaseState,
        method_name: str,
        context: NodeLifecycleContext
    ) -> BaseState:
        """call node method dynamically"""
        if method_name == 'execute':
            if not context.skip_execution:
                return await node.execute(state)
            return state
        
        elif method_name == 'route':
            next_node = node.route(state)
            from optorch.constants import StateKeys
            state[StateKeys.NEXT_NODE] = next_node
            return state
        
        elif hasattr(node, method_name):
            method = getattr(node, method_name)
            result = method(state)

            if hasattr(result, '__await__'):
                result = await result
            return result
        
        return state
