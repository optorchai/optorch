"""constraint registry - manages constraint providers"""

from typing import Optional, Type
from optorch.registry import Registry
from optorch.identity.authorization.constraints.provider import ConstraintProvider
from optorch.identity.authorization.constraints.config import ConstraintConfig, BaseConstraintConfig
from optorch.identity.authorization.constraints.models import ConstraintContext
import logging

logger = logging.getLogger(__name__)


class ConstraintRegistry:
    """registry for constraint providers
    
    manages built-in and custom constraints
    follows optorch registry pattern - instance-based, no singletons
    """
    
    def __init__(self):
        self._providers = Registry[Type[ConstraintProvider]]()
        self._register_builtins()
    
    def _register_builtins(self):
        """register built-in constraint providers"""
        from optorch.identity.authorization.constraints.time import TimeConstraint
        from optorch.identity.authorization.constraints.location import LocationConstraint
        from optorch.identity.authorization.constraints.resource import ResourceConstraint
        from optorch.identity.authorization.constraints.context import ContextConstraint
        
        self.register("time", TimeConstraint)
        self.register("location", LocationConstraint)
        self.register("resource", ResourceConstraint)
        self.register("context", ContextConstraint)
        logger.debug("registered builtin constraint providers: time, location, resource, context")
    
    def register(self, name: str, provider_class: Type[ConstraintProvider]) -> None:
        """register constraint provider class"""
        self._providers.register(name, provider_class)
        logger.debug(f"registered constraint provider: {name}")
    
    def has(self, name: str) -> bool:
        """check if constraint type registered"""
        return self._providers.has(name)
    
    def get(self, name: str) -> Type[ConstraintProvider]:
        """get constraint provider class by name"""
        return self._providers.get(name)
    
    def list_providers(self) -> list[str]:
        """list registered constraint types"""
        return self._providers.list_keys()
    
    def create(self, config: ConstraintConfig) -> Optional[ConstraintProvider]:
        """create constraint instance from config"""
        if not config.enabled:
            logger.debug(f"constraint {config.type} disabled")
            return None
        
        if config.type == "custom" and config.custom_class:
            return self._create_custom(config)
        
        if not self._providers.has(config.type):
            logger.warning(f"unknown constraint type: {config.type}")
            return None
        
        provider_class = self._providers.get(config.type)
        
        type_config: Optional[BaseConstraintConfig] = None
        if config.type == "time" and config.time:
            type_config = config.time
        elif config.type == "location" and config.location:
            type_config = config.location
        elif config.type == "resource" and config.resource:
            type_config = config.resource
        elif config.type == "context" and config.context:
            type_config = config.context
        
        if type_config is None:
            logger.warning(f"missing config for constraint type: {config.type}")
            return None

        return provider_class(type_config)  # type: ignore[call-arg]
    
    def _create_custom(self, config: ConstraintConfig) -> Optional[ConstraintProvider]:
        """create custom constraint from class path"""
        if not config.custom_class:
            logger.error("custom constraint requires custom_class")
            return None
        
        try:
            module_path, class_name_part = config.custom_class.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name_part])
            custom_class = getattr(module, class_name_part)
            return custom_class(config.custom_config or {})
        except Exception as e:
            logger.error(f"failed to create custom constraint: {e}")
            return None
    
    def evaluate_all(self, constraints: list[ConstraintConfig], context: ConstraintContext) -> bool:
        """evaluate multiple constraints (AND logic)"""
        for config in constraints:
            provider = self.create(config)
            if provider and not provider.evaluate(context):
                logger.debug(f"constraint {config.type} failed")
                return False
        return True
