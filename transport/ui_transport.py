"""UI transport health check registry"""
from optorch.logging import get_logger
from optorch.registry import Registry
from typing import Optional, TYPE_CHECKING, Dict, Callable, Any
import asyncio

if TYPE_CHECKING:
    from optorch.transport.config import TransportConfig
    from optorch.transport.base import BaseTransport

logger = get_logger(__name__)


class UITransportRegistry(Registry[type['BaseTransport']]):
    """Registry for UI transport backends - stores class references for JIT instantiation"""
    
    def __init__(self, config: Optional['TransportConfig'] = None):
        super().__init__()
        from optorch.transport.config import TransportConfig
        self.config = config or TransportConfig()
        self._providers: Dict[str, 'BaseTransport'] = {}
        self._auto_register()
    
    def _auto_register(self):
        """auto-register enabled transport providers via AutoLoader"""
        from optorch.loader.auto_loader import AutoLoader
        
        enabled_providers = {}
        for field_name, field_value in self.config.model_dump().items():
            if isinstance(field_value, dict) and field_value.get('enabled'):
                class_name = f"{field_name.capitalize()}Transport"
                enabled_providers[field_name] = class_name
        
        if enabled_providers:
            AutoLoader.register(self, enabled_providers, "optorch.transport.providers", instantiate=False)
    
    def list_available(self) -> list[dict[str, str | bool | dict]]:
        """list all transport providers with enabled status and configuration"""
        providers = []
        for field_name, field_value in self.config.model_dump().items():
            if isinstance(field_value, dict):
                enabled = field_value.get('enabled', False)
                
                provider_info: dict[str, Any] = {
                    "name": field_name,
                    "enabled": enabled
                }
                
                if enabled:
                    provider_config = getattr(self.config, field_name)
                    public_fields = getattr(provider_config, 'public_fields', ['enabled'])
                    public_config = {k: v for k, v in field_value.items() if k in public_fields}
                    provider_info["config"] = public_config
                
                providers.append(provider_info)
        return providers
    
    def get_active(self) -> Optional['BaseTransport']:
        """Get currently selected transport based on active_provider config"""
        active_name = self.config.active_provider
        
        if not active_name:
            for field_name, field_value in self.config.model_dump().items():
                if field_name == 'active_provider':
                    continue
                if isinstance(field_value, dict) and field_value.get('enabled', False):
                    active_name = field_name
                    break
        
        if active_name and self.has(active_name):
            return self._get_provider(active_name)
        
        return None
    
    def _get_provider(self, transport_name: str) -> Optional['BaseTransport']:
        """get or create singleton provider instance"""
        if transport_name not in self._providers:
            provider_config = getattr(self.config, transport_name)
            if getattr(provider_config, 'enabled', False):
                transport_class = self.get(transport_name)
                self._providers[transport_name] = transport_class(provider_config)
        return self._providers.get(transport_name)
    
    def subscribe_all(self, channel: str, callback: Callable) -> None:
        """subscribe to channel on ALL enabled transports"""
        for transport_name in self.list_keys():
            provider_config = getattr(self.config, transport_name, None)
            if provider_config and getattr(provider_config, 'enabled', False):
                instance = self._get_provider(transport_name)
                if instance:
                    coro = instance.subscribe(channel, callback)
                    
                    try:
                        loop = asyncio.get_running_loop()
                        asyncio.create_task(coro)
                    except RuntimeError:
                        asyncio.run(coro)
                    
                    logger.info(f"Subscribed to {transport_name} transport: {channel}")
    
    def unsubscribe_all(self, channel: str, callback: Callable) -> None:
        """unsubscribe from channel on ALL enabled transports"""
        for transport_name, instance in self._providers.items():
            coro = instance.unsubscribe(channel, callback)
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(coro)
                else:
                    loop.run_until_complete(coro)
            except RuntimeError:
                asyncio.run(coro)
            
            logger.info(f"Unsubscribed from {transport_name} transport: {channel}")
        return None
    
    async def check_health(self, backend_type: str, **kwargs: Any):
        """Check health of UI transport backend via touchfile/probe test
        
        Args:
            backend_type: Type of backend (file, redis, kafka)
            **kwargs: Probe parameters (probe_id, timeout, source)
            
        Returns:
            Health status response
        """
        from optorch.transport.base import TransportHealthResponse, TransportProbeRequest
        
        transport_class = self.get_optional(backend_type)
        if not transport_class:
            return TransportHealthResponse(
                status="error",
                error=f"Unknown backend type: {backend_type}. Supported: {', '.join(self.list_keys())}"
            )
        
        provider_config = getattr(self.config, backend_type, None)
        if not provider_config:
            return TransportHealthResponse(
                status="error",
                error=f"No configuration found for {backend_type} transport"
            )
        
        if 'source' not in kwargs:
            kwargs['source'] = 'ui-server'
        
        request = TransportProbeRequest(**kwargs)
        
        transport = transport_class(provider_config)
        return await transport.check_health(request)
