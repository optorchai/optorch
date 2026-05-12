"""protection layer - UMA 2.0 resource protection"""

from optorch.identity.protection.manager import ProtectionManager
from optorch.identity.protection.registry import ProtectionRegistry
from optorch.identity.protection.config import ProtectionConfig
from optorch.identity.protection.enforcement import (
    EnforcementRegistry,
    EnforcementResult,
    EnforcementStrategy,
    BlockEnforcement,
    InteractiveEnforcement,
    RouteEnforcement,
    WarnEnforcement,
)

__all__ = [
    "ProtectionManager",
    "ProtectionRegistry",
    "ProtectionConfig",
    "EnforcementRegistry",
    "EnforcementResult",
    "EnforcementStrategy",
    "BlockEnforcement",
    "InteractiveEnforcement",
    "RouteEnforcement",
    "WarnEnforcement",
]
