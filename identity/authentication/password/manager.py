from typing import Optional, Any
from optorch.identity.authentication.password.provider import PasswordProvider
from optorch.identity.authentication.password.config import PasswordManagerConfig
from optorch.registry import Registry
from optorch.errors import ConfigurationError
from optorch.logging import get_logger

logger = get_logger(__name__)


class PasswordManager:
    """Registry-based password manager - delegates to provider implementations"""
    
    def __init__(self, config: Optional[PasswordManagerConfig] = None):
        self.config = config or PasswordManagerConfig()
        self.providers: Registry[Any] = Registry()
        self._register_builtin_providers()
        
        provider_type = self.config.provider
        self.provider = self._initialize_provider(provider_type)
        
        logger.info(f"PasswordManager initialized with provider: {provider_type}")
    
    def _register_builtin_providers(self):
        """Register built-in providers"""
        from optorch.identity.authentication.password.providers.nist import NISTPasswordProvider
        from optorch.identity.authentication.password.providers.enterprise import EnterprisePasswordProvider
        from optorch.identity.authentication.password.providers.argon2 import Argon2PasswordProvider
        
        self.providers.register("nist", NISTPasswordProvider)
        self.providers.register("enterprise", EnterprisePasswordProvider)
        self.providers.register("argon2", Argon2PasswordProvider)
    
    def _initialize_provider(self, provider_type: str) -> PasswordProvider:
        """Initialize provider from config"""
        if not self.providers.has(provider_type):
            raise ConfigurationError(
                f"Unknown password provider: {provider_type}",
                details={
                    "provider": provider_type,
                    "available": self.providers.list_keys()
                }
            )
        
        provider_class = self.providers.get(provider_type)
        provider_config = getattr(self.config, provider_type, None)
        
        if provider_config is None:
            raise ConfigurationError(
                f"No config found for password provider: {provider_type}",
                details={
                    "provider": provider_type,
                    "config_attributes": [attr for attr in dir(self.config) if not attr.startswith('_')]
                }
            )
        
        return provider_class(provider_config)
    
    def validate(self, password: str, context: Optional[dict] = None) -> None:
        """Validate password using configured provider"""
        self.provider.validate(password, context)
    
    def hash(self, password: str) -> str:
        """Hash password using configured provider"""
        return self.provider.hash(password)
    
    def verify(self, password: str, password_hash: str) -> bool:
        """Verify password using configured provider"""
        return self.provider.verify(password, password_hash)
    
    def generate_temporary(self) -> str:
        """Generate temporary password using configured provider"""
        return self.provider.generate_temporary()
    
    def strength_score(self, password: str) -> int:
        """Calculate strength score using configured provider"""
        return self.provider.strength_score(password)
