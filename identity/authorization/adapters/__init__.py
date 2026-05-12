"""authorization adapters - interactive enforcement and config adapters"""

from typing import TYPE_CHECKING, Optional, Literal, cast
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.container import ApplicationContainer

logger = get_logger(__name__)


def register_authorization_adapter(
    risk_threshold: Literal["low", "medium", "high", "critical"] = "high"
) -> None:
    """register authorization adapter with interact extension
    
    call this from identity manager initialization to enable
    interactive authorization enforcement
    """
    from extensions.interact.registry import AdapterRegistry
    from optorch.identity.authorization.adapters.authorization_adapter import (AuthorizationAdapter, AuthorizationAdapterConfig)
    
    config = AuthorizationAdapterConfig(timeout=600, risk_threshold=risk_threshold)
    
    AdapterRegistry.register(
        name="authorization",
        adapter_class=AuthorizationAdapter,
        config=config.model_dump(),
        enabled=True,
        is_global=False
    )
    
    logger.info(f"registered authorization adapter (risk_threshold={risk_threshold})")


def init_interactive_authorization(container: "ApplicationContainer") -> None:
    """initialize interactive authorization from container
    
    wires AuthorizationManager to InteractionManager via adapter
    """
    interaction_manager = getattr(container, "interaction_manager", None)
    if not interaction_manager:
        logger.debug("interaction_manager not available, skipping authorization adapter registration")
        return
    
    identity_manager = container.identity
    if not identity_manager:
        logger.debug("identity manager not available, skipping authorization adapter registration")
        return
    
    raw_threshold = container.config_manager.get("authorization.interactive_risk_threshold", "high")
    valid_thresholds = {"low", "medium", "high", "critical"}
    risk_threshold = cast(Literal["low", "medium", "high", "critical"], raw_threshold if raw_threshold in valid_thresholds else "high")
    
    register_authorization_adapter(risk_threshold=risk_threshold)


def register_authorization_intent(
    container: "ApplicationContainer",
    enabled: bool = True,
    default_enforcement: Literal["block", "interactive", "warn"] = "block",
    default_risk_level: Literal["low", "medium", "high", "critical"] = "medium"
) -> None:
    """register authorization intent with node controller
    
    call this from identity initialization to enable node-level access control
    """
    from optorch.identity.authorization.intents import AuthorizationIntent
    
    identity_manager = container.identity
    if not identity_manager:
        logger.debug("identity manager not available, skipping authorization intent registration")
        return
    
    node_controller = getattr(container, "node_controller", None)
    if not node_controller:
        logger.debug("node_controller not available, skipping authorization intent registration")
        return
    
    authz_intent = AuthorizationIntent(
        authz_manager=identity_manager.authz,
        enabled=enabled,
        default_enforcement=default_enforcement,
        default_risk_level=default_risk_level
    )
    
    node_controller.intent_registry.register(key="authorization", item=authz_intent)
    logger.info(f"registered authorization intent (enforcement={default_enforcement})")

