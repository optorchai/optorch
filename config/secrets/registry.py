"""secret provider registry - instance-based registry pattern"""

from typing import Dict, Type, Optional, Any
from optorch.errors.exceptions import ConfigurationError
from optorch.logging import get_logger
from optorch.config.secrets.provider import SecretProvider

logger = get_logger(__name__)


class SecretProviderRegistry:
    """instance-based registry for secret providers"""
    
    def __init__(self):
        self._registry: Dict[str, Type[SecretProvider]] = {}
        self._default_type: str = "environment"
        self._register_builtins()
    
    def _register_builtins(self) -> None:
        """register framework providers"""
        from optorch.config.secrets.providers.environment import EnvironmentSecretProvider
        from optorch.config.secrets.providers.dict import DictSecretProvider
        
        self.register("environment", EnvironmentSecretProvider)
        self.register("dict", DictSecretProvider)
        logger.debug("registered builtin secret providers: environment, dict")
    
    def register(self, provider_type: str, provider_class: Type[SecretProvider]) -> None:
        """register provider type
        
        args:
            provider_type: registry key
            provider_class: provider implementation class
        """
        if provider_type in self._registry:
            logger.warning(f"overwriting secret provider: {provider_type}")
        self._registry[provider_type] = provider_class
        logger.debug(f"registered {provider_type} -> {provider_class.__name__}")
    
    def create(
        self,
        provider_type: Optional[str] = None,
        **kwargs: Any
    ) -> SecretProvider:
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
                f"unknown secret provider: {provider_type}",
                details={
                    "provider_type": provider_type,
                    "available": list(self._registry.keys())
                }
            )
        
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
    
    def list_providers(self) -> Dict[str, Type[SecretProvider]]:
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
        logger.info(f"default secret provider set to: {provider_type}")
    
    def has(self, provider_type: str) -> bool:
        """check if provider registered"""
        return provider_type in self._registry
