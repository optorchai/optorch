"""Dependency injection container for optorch services."""

from typing import Dict, Any, Optional, TYPE_CHECKING, Protocol

from optorch.errors.exceptions import ConfigurationError
from optorch.extension_registry import ExtensionRegistry

if TYPE_CHECKING:
    from optorch.config.manager import ConfigManager
    from optorch.session.session_manager import SessionManager
    from optorch.controller.node_controller import NodeController
    from optorch.lifecycle.lifecycle_executor import LifecycleExecutor
    from optorch.history.manager import History
    from optorch.cache.manager import CacheManager
    from optorch.tools.tool_registry import ToolRegistry
    from optorch.intents.intent_registry import IntentRegistry
    from optorch.transformers.transformer_registry import TransformerRegistry
    from optorch.llm.llm_registry import LLMRegistry
    from optorch.llm.manager import LLMManager
    from optorch.llm.prompt_manager import PromptManager
    from optorch.storage.manager import StorageManager
    from optorch.transport.ui_transport import UITransportRegistry
    from optorch.events.event_emitter import EventEmitter
    from optorch.identity.manager import IdentityManager


class ErrorHandlerProtocol(Protocol):
    def handle_error(self, error: Exception, context: Any) -> None: ...


class MetricsManagerProtocol(Protocol):
    def record_metric(self, name: str, value: float) -> None: ...


class FilterManagerProtocol(Protocol):
    def apply_filters(self, data: Any) -> Any: ...


class RegistryProtocol(Protocol):
    def get(self, name: str) -> Any: ...
    def register(self, name: str, item: Any) -> None: ...


class ApplicationContainer:
    """
    Container holding all optorch services.
    Manages service lifecycle
    """
    
    def __init__(self, config_manager: 'ConfigManager', config: Optional[Dict[str, Any]] = None):
        """
        Initialize all services from config.
        
        Args:
            config_manager: ConfigManager instance (required)
            config: Optional config dict override (defaults to config_manager.optorch.model_dump())
        """
        self.config_manager = config_manager
        self.config = config if config is not None else config_manager.optorch.model_dump()
        self.event_emitter: Optional['EventEmitter'] = None
        self.session_manager: Optional['SessionManager'] = None
        self.error_handler: Optional[ErrorHandlerProtocol] = None
        self.metrics_manager: Optional[MetricsManagerProtocol] = None
        self.history: Optional['History'] = None
        self.cache_manager: Optional['CacheManager'] = None
        self.filter_manager: Optional[FilterManagerProtocol] = None
        self.intent_registry: Optional['IntentRegistry'] = None
        self.tool_registry: Optional['ToolRegistry'] = None
        self.transformer_registry: Optional['TransformerRegistry'] = None
        self.llm_registry: Optional['LLMRegistry'] = None
        self.llm_manager: Optional['LLMManager'] = None
        self.prompt_manager: Optional['PromptManager'] = None
        self.lifecycle_executor: Optional['LifecycleExecutor'] = None
        self.node_controller: Optional['NodeController'] = None
        self.storage_manager: Optional['StorageManager'] = None
        self.transport_registry: Optional['UITransportRegistry'] = None
        self.identity: Optional['IdentityManager'] = None
        self.extension_registry = ExtensionRegistry()
    
    async def initialize(self):
        """Async initialization for services needing DB/network setup"""
        pass
    
    async def cleanup(self):
        """Cleanup resources on shutdown"""
        pass
    
    def create_node_context(self, node: Optional[str] = None, phase: Optional[str] = None):
        """
        Create execution context for node operations.
        
        Args:
            node: Current node name (optional)
            phase: Current lifecycle phase (optional)
        
        Returns:
            NodeContext with service references
            
        Raises:
            RuntimeError: If required services not initialized
        """
        from optorch.controller.node_context import NodeContext
        
        if self.node_controller is None:
            raise ConfigurationError("NodeController not initialized in container")
        if self.session_manager is None:
            raise ConfigurationError("SessionManager not initialized in container")
        if self.history is None:
            raise ConfigurationError("History not initialized in container")
        if self.cache_manager is None:
            raise ConfigurationError("CacheManager not initialized in container")
        
        session_id = self.session_manager.get_id()
        if not session_id:
            raise ConfigurationError("No active session - call session_manager.set_current_session() first")
        
        if self.event_emitter is None:
            raise ConfigurationError("EventEmitter not initialized in container")
        
        return NodeContext(
            controller=self.node_controller,
            events=self.event_emitter,
            sessions=self.session_manager,
            history=self.history,
            cache=self.cache_manager,
            container=self,
            current_node_name=node,
            current_phase=phase
        )
