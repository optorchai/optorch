"""Orchestrator with instance-based dependency injection."""

import asyncio
from optorch.logging import get_logger
from optorch.types import AppHooksProtocol
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from optorch.config import ConfigManager
from optorch.state import StateFactory
from optorch.utils import generate_id
from optorch.events.decorators import emits
from optorch.constants import EventTypes, StateKeys

logger = get_logger(__name__)


class Orchestrator:
    """Instance-based orchestrator."""
    
    @classmethod
    def create(
        cls,
        config_path: Optional[str] = None,
        entry_node: Optional[str] = None,
        app_hooks: Optional[AppHooksProtocol] = None,
        config_manager: Optional[ConfigManager] = None,
        **overrides
    ):
        """Library entry point - sync wrapper for async initialization.
        
        Args:
            config_path: Path to config directory (default: "config")
            entry_node: Override default entry point node
            **overrides: Config overrides (e.g., llm="gpt-4", temperature=0.7)
                prompts: dict[str, str] | Callable[[str], str | None] | None
                    - dict: inline prompts {"tariff": "template..."}  
                    - callable: dynamic loader function(name) -> template
                prompts_dir: str - override default prompts directory
            
        Returns:
            Orchestrator instance ready for .execute() calls
            
        Example:
            orchestrator = Orchestrator.create()
            result = await orchestrator.execute("tariff", "Build pricing")
            
            # With inline prompts
            orchestrator = Orchestrator.create(
                prompts={"tariff": "You are a tariff specialist..."}
            )
            
            # With config overrides
            orchestrator = Orchestrator.create(
                llm="gpt-4o",
                temperature=0.7
            )
        
        Note:
            Cannot be called from within an async context (FastAPI, Jupyter async).
            Use create_async() instead if already in an event loop.
        """
        prompts = overrides.pop("prompts", None)
        prompts_dir = overrides.pop("prompts_dir", None)
        
        instance = cls(config_path, entry_node, prompts=prompts, prompts_dir=prompts_dir, app_hooks=app_hooks, config_manager=config_manager)
        
        # apply runtime config overrides
        for key, value in overrides.items():
            instance.config.set(key, value)
        
        # check if already in event loop
        try:
            loop = asyncio.get_running_loop()
            raise RuntimeError(
                "Orchestrator.create() cannot be called from async context. "
                "You're already in an event loop. Use Orchestrator.create_async() instead."
            )
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                asyncio.run(instance._initialize_async())
                return instance
            else:
                raise
    
    @classmethod
    async def create_async(
        cls,
        config_path: Optional[str] = None,
        entry_node: Optional[str] = None,
        app_hooks: Optional[AppHooksProtocol] = None,
        config_manager: Optional[ConfigManager] = None,
        **overrides
    ):
        """Library entry point for async contexts - no asyncio.run wrapper.
        
        Use when already in async context (FastAPI, Jupyter async, etc).
        
        Args:
            config_path: Path to config directory (default: "config")
            entry_node: Override default entry point node
            **overrides: Config overrides (e.g., llm="gpt-4", temperature=0.7)
                prompts: dict[str, str] | Callable[[str], str | None] | None
                    - dict: inline prompts {"tariff": "template..."}  
                    - callable: dynamic loader function(name) -> template
                prompts_dir: str - override default prompts directory
            
        Returns:
            Orchestrator instance ready for .execute() calls
            
        Example:
            orchestrator = await Orchestrator.create_async()
            result = await orchestrator.execute("tariff", "Build pricing")
            
            # With inline prompts
            orchestrator = await Orchestrator.create_async(
                prompts={"tariff": "You are a tariff specialist..."}
            )
            
            # With config overrides
            orchestrator = await Orchestrator.create_async(
                llm="gpt-4o",
                temperature=0.7
            )
        """
        prompts = overrides.pop("prompts", None)
        prompts_dir = overrides.pop("prompts_dir", None)
        
        instance = cls(config_path, entry_node, prompts=prompts, prompts_dir=prompts_dir, app_hooks=app_hooks, config_manager=config_manager)
        
        # apply runtime config overrides
        for key, value in overrides.items():
            instance.config.set(key, value)
        
        await instance._initialize_async()
        return instance
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        entry_node: Optional[str] = None,
        prompts: Optional[dict | object] = None,
        prompts_dir: Optional[str] = None,
        app_hooks: Optional[AppHooksProtocol] = None,
        config_manager: Optional[ConfigManager] = None
    ):
        from optorch.initializer import initialize
        
        self.config = config_manager if config_manager is not None else ConfigManager(config_path)
        self.entry_node = entry_node or self.config.get("routing.default_node")
        
        # store prompt overrides to pass to optorch init
        prompt_config_override = {}
        if prompts is not None:
            if isinstance(prompts, dict):
                prompt_config_override["inline_prompts"] = prompts
            elif callable(prompts):
                prompt_config_override["loader_callable"] = prompts
        
        if prompts_dir is not None:
            prompt_config_override["directory"] = prompts_dir
        
        # pass to optorch via config override
        optorch_override = {}
        if prompt_config_override:
            optorch_override["prompts"] = prompt_config_override
        
        self.container = initialize(config=self.config, config_override=optorch_override if optorch_override else None)
        
        if app_hooks:
            app_hooks(self.container)
    
    async def _initialize_async(self):
        """async initialization"""
        from optorch.initializer import initialize_async
        await initialize_async(self.container, self.entry_node)
    
    def _new_session(self) -> str:
        """Generate new session ID for execute() calls."""
        return generate_id()
    
    async def execute(
        self,
        node: str,
        message: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> dict:
        """Direct method call for library mode - returns pure dict.
        
        Args:
            node: Node name to execute (e.g. "tariff", "cost")
            message: User message to process
            session_id: Optional session ID (generated if not provided)
            **kwargs: Additional state data (tone, etc)
            
        Returns:
            dict with execution result (not StreamingState)
            
        Example:
            result = await orchestrator.execute("tariff", "Build pricing")
        """
        assert self.container.session_manager is not None, "SessionManager must be initialized"
        
        if session_id is None:
            session_id = self._new_session()
        
        self.container.session_manager.set_current_session(session_id)
        
        state_data = {
            StateKeys.SESSION_ID: session_id,
            StateKeys.USER_MESSAGE: message,
            **kwargs
        }
        
        result = await self.run(state_data, entry_node=node)
        
        if hasattr(result, 'to_dict'):
            return result.to_dict()
        elif isinstance(result, dict):
            return result
        else:
            return {"result": str(result)}
    
    @emits(EventTypes.MESSAGE)
    async def run(
        self,
        state=None,
        entry_node: Optional[str] = None,
        tone: Optional[str] = None
    ):
        """
        run orchestration with instance-based services.
        
        creates NodeContext for execution.
        """
        # validate required services initialized
        assert self.container.node_controller is not None, "NodeController must be initialized"
        assert self.container.session_manager is not None, "SessionManager must be initialized"
        
        if not hasattr(state, 'to_dict'):
            state = StateFactory.create(state)
        
        assert state is not None, "State must be initialized"
        
        if tone:
            from optorch.llm.fragments.base import Fragment
            self.container.node_controller.prompt_manager.fragment.register(Fragment("tone", tone))
        
        # set current session in session manager
        self.container.session_manager.set_current_session(state.get(StateKeys.SESSION_ID))
        
        # create context for this execution
        node = entry_node or self.entry_node
        context = self.container.create_node_context(node=node)
        
        # dispatch with context
        return await self.container.node_controller.dispatch(node, state, context)



