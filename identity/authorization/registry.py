"""authorization provider registry - config-driven provider initialization"""

from typing import Any, Optional, TYPE_CHECKING, Union
from optorch.registry import Registry
from optorch.identity.authorization.provider import AuthorizationProvider
from optorch.logging import get_logger
import inspect

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.container import ApplicationContainer
    from optorch.identity.config import AuthorizationConfig

logger = get_logger(__name__)


class AuthorizationProviderRegistry(Registry[type[AuthorizationProvider]]):
    """registry for authorization providers (Casbin, OPA, XACML)"""

    def __init__(self):
        super().__init__()
        self._register_builtins()

    def _register_builtins(self) -> None:
        """register framework authorization providers"""
        from optorch.identity.authorization.providers.casbin_provider import CasbinProvider
        from optorch.identity.authorization.providers.opa import OPAProvider
        from optorch.identity.authorization.providers.memory import MemoryProvider

        self.register("casbin", CasbinProvider)
        self.register("opa", OPAProvider)
        self.register("memory", MemoryProvider)

        logger.debug("registered builtin authorization providers: casbin, opa, memory")

    def create_provider_from_config(
        self,
        config: Union["AuthorizationConfig", dict[str, Any]],
        storage_manager: Optional["StorageManager"] = None,
        constraint_registry: Optional[Any] = None,
    ) -> AuthorizationProvider:
        """create provider from config using registry
        
        Args:
            config: authorization configuration
            storage_manager: for policy storage
            constraint_registry: for ABAC constraint evaluation
        
        Returns:
            configured authorization provider
        """
        provider_type = getattr(config, "provider", "memory")

        if not self.has(provider_type):
            logger.warning(f"unknown authorization provider: {provider_type}, falling back to memory")
            provider_type = "memory"
        
        provider_class = self.get(provider_type)
        init_sig = inspect.signature(provider_class.__init__)
        params = list(init_sig.parameters.keys())
        kwargs: dict[str, Any] = {}
        
        if "container" in params:
            from typing import cast
            
            class _MinimalContainer:
                def __init__(self, cfg: Any, storage: Optional["StorageManager"]) -> None:
                    self.config = cfg
                    self.config_manager: Any = None
                    self.storage_manager = storage

                def get(self, key: str, default: Any = None) -> Any:
                    return default

            kwargs["container"] = cast("ApplicationContainer", _MinimalContainer(config, storage_manager))
        
        if "config" in params:
            config_dict: dict[str, Any]
            if provider_type == "casbin":
                config_dict = {"model_path": getattr(config, "casbin_model_path", None)}
            elif isinstance(config, dict):
                config_dict = config
            elif hasattr(config, "model_dump"):
                config_dict = config.model_dump()
            else:
                config_dict = {}
            kwargs["config"] = config_dict
        
        if "storage_manager" in params and storage_manager is not None:
            kwargs["storage_manager"] = storage_manager
        
        if "constraint_registry" in params and constraint_registry is not None:
            kwargs["constraint_registry"] = constraint_registry
        
        return provider_class(**kwargs)
