"""ABAC constraint system - registry-based constraint evaluation

follows optorch registry pattern - minimal exports, autoloader for discovery

usage:
    from optorch.identity.authorization.constraints import (
        ConstraintProvider,
        ConstraintRegistry,
        ConstraintContext
    )
    
    registry = ConstraintRegistry()  # builtins auto-register
    config = ConstraintConfig(type="time", time={...})
    provider = registry.create(config)
    result = provider.evaluate(context)
"""

from optorch.identity.authorization.constraints.provider import ConstraintProvider
from optorch.identity.authorization.constraints.registry import ConstraintRegistry
from optorch.identity.authorization.constraints.models import ConstraintContext

__all__ = ["ConstraintProvider", "ConstraintRegistry", "ConstraintContext"]
