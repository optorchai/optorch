"""authentication provider registry - config-driven provider initialization"""

from typing import Any, Optional, TYPE_CHECKING
from optorch.registry import Registry
from optorch.identity.authentication.provider import AuthenticationProvider
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.cache.manager import CacheManager
    from optorch.config.secrets.provider import SecretProvider

logger = get_logger(__name__)


class AuthenticationProviderRegistry(Registry[type[AuthenticationProvider]]):
    """registry for authentication providers (OIDC, SAML, JWT, Builtin)
    
    same pattern as LLMManager, PasswordManager - transparent config-driven initialization
    """

    def __init__(self):
        super().__init__()
        self._register_builtins()

    def _register_builtins(self) -> None:
        """register framework authentication providers"""
        from optorch.identity.authentication.providers.jwt import JWTProvider
        from optorch.identity.authentication.providers.builtin.provider import BuiltinAuthenticationProvider
        from optorch.identity.authentication.providers.oidc import OIDCProvider
        from optorch.identity.authentication.providers.saml import SAMLProvider

        self.register("jwt", JWTProvider)
        self.register("builtin", BuiltinAuthenticationProvider)
        self.register("oidc", OIDCProvider)
        self.register("saml", SAMLProvider)

        logger.debug("registered builtin authentication providers: jwt, builtin, oidc, saml")

    def create_providers_from_config(
        self,
        config: Any,
        storage_manager: Optional["StorageManager"] = None,
        cache_manager: Optional["CacheManager"] = None,
        secrets_manager: Optional["SecretProvider"] = None,
        notification_manager: Optional[Any] = None,
    ) -> list[AuthenticationProvider]:
        """create providers from config, sorted by priority
        
        Args:
            config: authentication configuration
            storage_manager: for refresh token storage, user lookup
            cache_manager: for token blacklisting
            secrets_manager: for on-demand secret fetching (OIDC/SAML)
        
        Returns:
            list of configured providers, sorted by priority (highest first)
        """
        providers = []

        if hasattr(config, "jwt") and config.jwt is not None:
            from optorch.identity.authentication.providers.jwt import JWTProvider
            from optorch.identity.authentication.providers.config import JWTProviderConfig
            
            jwt_config = config.jwt if isinstance(config.jwt, JWTProviderConfig) else JWTProviderConfig(**config.jwt if isinstance(config.jwt, dict) else {})
            
            resolved_secret = jwt_config.secret
            if not resolved_secret and jwt_config.secret_key_secret and secrets_manager:
                resolved_secret = secrets_manager.get(jwt_config.secret_key_secret)
                if not resolved_secret:
                    logger.error(f"JWT secret not found in secret provider: {jwt_config.secret_key_secret}")
            
            provider = JWTProvider(
                storage_manager=storage_manager,
                config=jwt_config,
                secret_provider=secrets_manager,
                resolved_secret=resolved_secret,
            )
            priority = getattr(jwt_config, "priority", 100)
            providers.append((priority, provider))
            logger.debug(f"created jwt provider (priority={priority})")

        if hasattr(config, "builtin") and config.builtin is not None:
            from optorch.identity.authentication.providers.builtin.provider import BuiltinAuthenticationProvider
            provider = BuiltinAuthenticationProvider(
                storage_manager=storage_manager,
                notification_manager=notification_manager,
                secret_provider=secrets_manager,
                config=config.builtin,
            )
            providers.append((getattr(config.builtin, "priority", 10), provider))
            logger.debug(f"created builtin provider (priority={getattr(config.builtin, 'priority', 10)})")

        if hasattr(config, "custom_providers"):
            for provider_name, provider_config in config.custom_providers.items():
                if not self.has(provider_name):
                    logger.warning(f"unknown authentication provider: {provider_name} (skipped)")
                    continue

                provider_class = self.get(provider_name)
                provider = provider_class(**provider_config)
                providers.append((provider_config.get("priority", 50), provider))
                logger.debug(f"created custom provider {provider_name} (priority={provider_config.get('priority', 50)})")

        providers.sort(key=lambda x: x[0], reverse=True)
        return [p[1] for p in providers]
