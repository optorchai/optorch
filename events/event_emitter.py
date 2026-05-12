"""EventEmitter - optorch entry point for events"""
from typing import Dict, Any, Optional, TYPE_CHECKING
import time
from optorch.logging import get_logger
from optorch.events.listener_manager import ListenerManager
from optorch.events.backend_manager import BackendManager
from optorch.filters.filter_manager import FilterManager
from optorch.tenant_context import TenantContext

if TYPE_CHECKING:
    from optorch.config.manager import ConfigManager

logger = get_logger(__name__)


class EventEmitter:
    """Optorch entry point for event emission and distribution"""
    
    def __init__(self, filter_manager: Optional[FilterManager] = None, distribution_strategy: Optional[Any] = None, config_manager: Optional['ConfigManager'] = None):
        """
        Initialize event emitter with new multi-backend architecture.
        
        Args:
            filter_manager: FilterManager for transformation filters (PII removal, context injection)
            distribution_strategy: Strategy for distributing listeners to backends (defaults to TagBasedStrategy)
            config_manager: ConfigManager for secret access (creates new if None)
        """
        self._listeners = ListenerManager()
        self._backends = BackendManager(self._listeners, strategy=distribution_strategy)
        self._filter_manager = filter_manager or FilterManager()
        self._enabled = True
        self._config_manager = config_manager
    
    @classmethod
    def from_config(cls, config_manager: 'ConfigManager', config: Optional[Dict[str, Any]] = None) -> "EventEmitter":
        """
        Create EventEmitter from optorch config.
        
        Delegates to EventEmitterFactory for all config loading.
        
        Args:
            config_manager: ConfigManager (required)
            config: Optional config dict override
        """
        from optorch.events.event_emitter_factory import EventEmitterFactory
        return EventEmitterFactory.from_config(config_manager=config_manager, config=config)
    
    @property
    def listeners(self) -> ListenerManager:
        """access listener registry"""
        return self._listeners
    
    @property
    def backends(self) -> BackendManager:
        """access backend manager"""
        return self._backends
    
    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None, state: Optional[Any] = None) -> None:
        """
        Emit event through transformation → distribution.
        
        Auto-includes tenant context (application_id, user_id, client_id, request_id).
        Auto-injects node_name from state[StateKeys.CURRENT_NODE] if available.
        
        Args:
            event_type: Event type string (e.g., "llm.start", "node.complete")
            data: Event payload dict
            state: Optional State object to extract node_name from
        """
        if not self._enabled:
            return
        
        tenant_ctx = TenantContext.get_dict()
        
        # auto-inject node_name from state if available
        node_name = None
        if state and not (data and "node_name" in data):
            try:
                from optorch.constants import StateKeys
                node_name = state.get(StateKeys.CURRENT_NODE)
            except Exception:
                pass
        
        event = {"type": event_type, "timestamp": time.time(), **tenant_ctx, **(data or {})}
        
        if node_name and "node_name" not in event:
            event["node_name"] = node_name
        
        # transformation filters (PII removal, context injection, etc)
        if self._config_manager is None:
            from optorch.config.manager import ConfigManager
            self._config_manager = ConfigManager()
            self._config_manager.set_event_emitter(self)
        environment = self._config_manager.secret_provider.get("OPTORCH_ENV") or "development"
        filtered_event = self._filter_manager.for_target("events", environment).apply(event)
        
        if filtered_event is None:
            return
        
        self._backends.notify(event_type, filtered_event)
    
    def enable(self) -> None:
        """enable event emission"""
        self._enabled = True
    
    def disable(self) -> None:
        """disable event emission"""
        self._enabled = False
    
    def register_listener(self, listener: Any, **kwargs) -> None:
        """backwards compat - register listener"""
        self._listeners.add(listener, **kwargs)
    
    def remove_listener(self, listener: Any) -> None:
        """backwards compat - remove listener"""
        self._listeners.remove(listener)
    
    def clear_listeners(self) -> None:
        """backwards compat - clear all listeners"""
        self._listeners._entries.clear()
        self._listeners._listener_map.clear()
    
    async def close(self) -> None:
        """cleanup all backends - closes expensive connections"""
        await self._backends.close_all()
