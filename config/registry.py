"""config provider registry - instance-based registry pattern"""

from typing import Dict, Type, Optional, Any
from optorch.errors.exceptions import ConfigurationError
from optorch.logging import get_logger
from optorch.config.provider import ConfigProvider

logger = get_logger(__name__)


class ConfigProviderRegistry:
    """instance-based registry for config providers"""
    
    def __init__(self):
        self._registry: Dict[str, Type[ConfigProvider]] = {}
        self._default_type: str = "yaml"
        self._register_builtins()
    
    def _register_builtins(self) -> None:
        """register framework providers"""
        from optorch.config.providers.yaml import YamlConfigProvider
        from optorch.config.providers.dict import DictConfigProvider
        from optorch.config.providers.database import DatabaseConfigProvider
        
        self.register("yaml", YamlConfigProvider)
        self.register("dict", DictConfigProvider)
        self.register("database", DatabaseConfigProvider)
        logger.debug("registered builtin config providers: yaml, dict, database")
    
    def register(self, provider_type: str, provider_class: Type[ConfigProvider]) -> None:
        """register provider type
        
        args:
            provider_type: registry key
            provider_class: provider implementation class
        """
        if provider_type in self._registry:
            logger.warning(f"overwriting config provider: {provider_type}")
        self._registry[provider_type] = provider_class
        logger.debug(f"registered {provider_type} -> {provider_class.__name__}")
    
    def create(
        self,
        provider_type: Optional[str] = None,
        **kwargs: Any
    ) -> ConfigProvider:
        """create provider instance
        
        args:
            provider_type: registry key (if None, uses default)
            **kwargs: passed to provider constructor
        
        raises:
            ConfigurationError: unknown provider or creation failed
        """
        provider_type = provider_type or self._default_type
        
        if provider_type not in self._registry:
            raise ConfigurationError(
                f"unknown config provider: {provider_type}",
                details={
                    "provider_type": provider_type,
                    "available": list(self._registry.keys())
                }
            )
        
        if provider_type == "database":
            from optorch.config.providers.yaml import YamlConfigProvider
            fallback = YamlConfigProvider(
                config_dir=kwargs.get("config_dir", "config"),
                config_file=kwargs.get("config_file"),
                secret_provider=kwargs.get("secret_provider")
            )
            kwargs["fallback_provider"] = fallback
        
        provider_class = self._registry[provider_type]
        try:
            return provider_class(**kwargs)
        except Exception as e:
            raise ConfigurationError(
                f"failed to create provider: {provider_type}",
                details={
                    "provider_type": provider_type,
                    "provider_class": provider_class.__name__,
                    "error": str(e)
                }
            ) from e
    
    def list_providers(self) -> Dict[str, Type[ConfigProvider]]:
        """get all registered providers"""
        return self._registry.copy()
    
    def set_default(self, provider_type: str) -> None:
        """change default provider type"""
        if provider_type not in self._registry:
            raise ConfigurationError(
                f"cannot set unknown default: {provider_type}",
                details={
                    "provider_type": provider_type,
                    "available": list(self._registry.keys())
                }
            )
        self._default_type = provider_type
        logger.info(f"default config provider set to: {provider_type}")
    
    def has(self, provider_type: str) -> bool:
        """check if provider registered"""
        return provider_type in self._registry
