"""Factory for creating EventEmitter instances from config"""
from typing import Dict, Any, Optional, Type, Protocol, TYPE_CHECKING
from optorch.logging import get_logger
from optorch.events.event_emitter import EventEmitter
from optorch.events.backend import EventBackend
from optorch.events.backends.local_backend import LocalBackend
from optorch.loader.auto_loader import AutoLoader
from optorch.utils.config import get_env

if TYPE_CHECKING:
    from optorch.config.manager import ConfigManager

logger = get_logger(__name__)


class BackendFactory(Protocol):
    """protocol for backends with from_config factory"""
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> EventBackend: ...


class EventEmitterFactory:
    """builds EventEmitter from config with AutoLoader discovery"""
    
    @staticmethod
    def from_config(
        config_manager: 'ConfigManager',
        config: Optional[Dict[str, Any]] = None,
        backends_base_package: Optional[str] = None,
        distribution_base_package: Optional[str] = None
    ) -> EventEmitter:
        """
        create EventEmitter from optorch config
        
        Args:
            config_manager: ConfigManager (required)
            config: Optional config dict override (defaults to config_manager.optorch.model_dump())
            backends_base_package: base package for backend discovery (defaults to env var or 'app.events.backends')
            distribution_base_package: base package for strategy discovery (defaults to env var or 'app.events.distribution')
        """
        cfg = config if config is not None else config_manager.optorch.model_dump()
        
        backends_pkg = backends_base_package or get_env("OPTORCH_EVENTS_BACKENDS_PACKAGE", "app.events.backends")
        distribution_pkg = distribution_base_package or get_env("OPTORCH_EVENTS_DISTRIBUTION_PACKAGE", "app.events.distribution")
        
        events_config = cfg.get("events", {})
        
        strategy = EventEmitterFactory._create_distribution_strategy(
            events_config.get("distribution", {}),
            distribution_pkg
        )
        
        emitter = EventEmitter(distribution_strategy=strategy, config_manager=config_manager)
        config_manager.set_event_emitter(emitter)
        
        listeners_config = events_config.get("listeners")
        if listeners_config:
            EventEmitterFactory._register_listeners(emitter, listeners_config)
        
        backends_config = events_config.get("backends")
        if backends_config:
            EventEmitterFactory._register_backends(emitter, backends_config, backends_pkg)
        
        return emitter
    
    @staticmethod
    def _register_listeners(emitter: EventEmitter, listeners_config: Dict[str, Any]) -> None:
        """register listeners from config with AutoLoader filters"""
        if not listeners_config:
            return
        
        from optorch.events.listeners import ConsoleListener, FileListener, PrometheusListener
        
        listener_classes = {
            "console": ConsoleListener,
            "file": FileListener,
            "prometheus": PrometheusListener
        }
        
        for name, config in listeners_config.items():
            if not config.get("enabled", True):
                continue
            
            listener_class = listener_classes.get(name)
            if listener_class:
                listener = listener_class()
                
                priority = config.get("priority", 50)
                tags = set(config.get("tags", []))
                tags.add("configured")
                
                event_filter = EventEmitterFactory._create_listener_filters(config)
                
                emitter.listeners.add(
                    listener, 
                    priority=priority, 
                    tags=tags if tags else None,
                    event_filter=event_filter
                )
    
    @staticmethod
    def _create_listener_filters(listener_config: Dict[str, Any]) -> Optional[Any]:
        """create filters for listener from config using AutoLoader"""
        filters = []
        
        if "event_types" in listener_config:
            event_types = listener_config["event_types"]
            if event_types:
                try:
                    filter_class = AutoLoader.load_class(
                        "EventTypePatternFilter",
                        "event_type_pattern",
                        "app.filters.events"
                    )
                    filters.append(filter_class(event_types))
                except ImportError as e:
                    logger.error(f"Failed to load EventTypePatternFilter: {e}")
        
        if "filters" in listener_config:
            for filter_config in listener_config["filters"]:
                filter_type = filter_config.get("type")
                if not filter_type:
                    continue
                
                class_name = f"{filter_type.title().replace('_', '')}Filter"
                
                try:
                    filter_class = AutoLoader.load_class(
                        class_name,
                        filter_type,
                        "app.filters.events"
                    )

                    filters.append(filter_class.from_config(filter_config))
                except ImportError as e:
                    logger.error(f"Failed to load filter {filter_type}: {e}")
        
        return filters if filters else None
    
    @staticmethod
    def _register_backends(
        emitter: EventEmitter,
        backends_config: Dict[str, Any],
        base_package: str
    ) -> None:
        """register backends using AutoLoader"""
        if not backends_config:
            return
        
        for name, config in backends_config.items():
            if not config.get("enabled", True):
                continue
            
            backend_type = config.get("type")
            if not backend_type:
                continue
            
            class_name = f"{backend_type.title().replace('_', '')}Backend"
            
            try:
                backend_class: Type[BackendFactory] = AutoLoader.load_class(
                    class_name,
                    f"{backend_type}_backend",
                    base_package
                )

                backend: EventBackend = backend_class.from_config(config)
                emitter.backends.add(name, backend)
            except ImportError as e:
                logger.error(f"Failed to load backend {backend_type}: {e}")
    
    @staticmethod
    def _create_distribution_strategy(
        distribution_config: Dict[str, Any],
        base_package: str
    ) -> Optional[Any]:
        """create distribution strategy using AutoLoader"""
        strategy_type = distribution_config.get("strategy", "tag_based")
        if not strategy_type:
            return None
        
        class_name = f"{strategy_type.title().replace('_', '')}Strategy"
        
        try:
            strategy_class = AutoLoader.load_class(
                class_name,
                f"{strategy_type}_strategy",
                base_package
            )
            return strategy_class()
        except ImportError as e:
            logger.error(f"Failed to load distribution strategy {strategy_type}: {e}")
            return None
