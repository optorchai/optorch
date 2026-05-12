"""transport package initializer"""
from optorch.logging import get_logger
from optorch.utils.config import get_env
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from optorch.container import ApplicationContainer
    from optorch.config import ConfigManager

logger = get_logger(__name__)


class TransportPackageInitializer:
    """initialize UI transport system"""
    
    @staticmethod
    def initialize(
        config_manager: 'ConfigManager',
        container: Optional['ApplicationContainer'] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """initialize transport registry from config
        
        Args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: Optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
        """
        from optorch.transport.ui_transport import UITransportRegistry
        from optorch.transport.config import TransportConfig
        from optorch.initializer_utils import extract_optorch_config
        
        if not container:
            logger.warning("No container provided - transport registry not initialized")
            return
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        if overrides:
            transport_dict = config_manager.merge_overrides("transport", overrides, isolate=True)
        else:
            transport_dict = optorch_config.get("transport", {})
        
        if "redis" in transport_dict and not transport_dict["redis"].get("connection"):
            redis_config = config_manager.get("storage.redis")
            if redis_config:
                transport_dict.setdefault("redis", {})["connection"] = redis_config
        
        if "kafka" in transport_dict:
            kafka_config = config_manager.get("enterprise.kafka")
            if kafka_config:
                base = kafka_config.model_dump() if hasattr(kafka_config, 'model_dump') else kafka_config
                overrides = transport_dict.get("kafka")
                
                if not overrides:
                    overrides = {}
                
                composed = {**base}
                for key, value in overrides.items():
                    if value is not None:
                        composed[key] = value
                
                transport_dict["kafka"] = composed
        
        transport_config = TransportConfig(**transport_dict) if isinstance(transport_dict, dict) else transport_dict
        container.transport_registry = UITransportRegistry(transport_config)
        
        config_manager.set_transport(container.transport_registry)
        
        logger.info("Transport registry initialized")
    
    @staticmethod
    async def initialize_async(container: Optional['ApplicationContainer'] = None) -> None:
        """async initialization - start transport responders for enabled providers
        
        Starts background tasks that listen for health check probes from UI server
        """
        if not container or not hasattr(container, 'transport_registry'):
            return
        
        registry = container.transport_registry
        if not registry:
            return
        
        config = registry.config
        
        logger.info("Starting transport responders...")
        
        cleanup_tasks = []
        for name in registry.list_keys():
            provider_config = getattr(config, name)
            if getattr(provider_config, 'enabled', False):
                transport = registry._get_provider(name)
                if transport:
                    started = await transport.start_responder()
                    if started:
                        cleanup_tasks.append(transport.stop_responder)
        
        async def cleanup_transports():
            for cleanup in cleanup_tasks:
                await cleanup()
        
        if cleanup_tasks:
            container.extension_registry.register("transport", cleanup=cleanup_transports)
        
        logger.info("✅ Transport responders initialized")
