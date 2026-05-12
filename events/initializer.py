"""Events package initializer - creates singleton EventEmitter"""
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.container import ApplicationContainer
    from optorch.config.manager import ConfigManager

from optorch.logging import get_logger

logger = get_logger(__name__)


class EventsPackageInitializer:
    """Initialize singleton event infrastructure"""
    
    @staticmethod
    def initialize(
        config_manager: 'ConfigManager',
        container: 'ApplicationContainer',
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Creates container.event_emitter from config.
        
        Args:
            config_manager: ConfigManager instance
            container: ApplicationContainer
            config: Optional optorch config dict override
            overrides: Runtime overrides
        """
        from optorch.events.event_emitter_factory import EventEmitterFactory
        from optorch.events.config import EventsConfig
        from optorch.initializer_utils import extract_optorch_config
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        if overrides and "events" in overrides:
            events_dict = config_manager.merge_overrides("events", overrides, isolate=True)
        else:
            events_dict = optorch_config.get("events", {})
        
        events_config = EventsConfig(**events_dict)
        
        container.event_emitter = EventEmitterFactory.from_config(
            config_manager=config_manager,
            config={"events": events_config.model_dump()}
        )
        
        logger.info("✅ Events package initialized - singleton emitter created")
