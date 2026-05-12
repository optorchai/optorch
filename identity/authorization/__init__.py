"""XACML 3.0 authorization system"""

from optorch.identity.authorization.models import Decision, Permission, Role, Resource
from optorch.identity.authorization.manager import AuthorizationManager
from optorch.identity.authorization.provider import AuthorizationProvider
from optorch.identity.authorization.exceptions import (
    PermissionDenied,
    AuthorizationError,
)

from optorch.identity.authorization.constraints import (
    ConstraintProvider,
    ConstraintRegistry,
    ConstraintContext,
)

from optorch.identity.authorization.constraints.config import (
    ConstraintConfig,
    TimeConstraintConfig,
    LocationConstraintConfig,
    ResourceConstraintConfig,
    ContextConstraintConfig,
)

from optorch.identity.authorization.constraints.models import (
    SubjectContext,
    ResourceContext,
    EnvironmentContext,
)

from optorch.identity.authorization.constraints.time import TimeConstraint
from optorch.identity.authorization.constraints.location import LocationConstraint
from optorch.identity.authorization.constraints.resource import ResourceConstraint
from optorch.identity.authorization.constraints.context import ContextConstraint

from optorch.identity.authorization.decorators import (
    require_permission,
    require_role,
    require_any_role,
    require_all_roles,
    business_hours_only,
    weekday_only,
    require_same_org,
    cost_limit
)

__all__ = [
    "Decision",
    "Permission",
    "Role",
    "Resource",
    "AuthorizationManager",
    "AuthorizationProvider",
    "PermissionDenied",
    "AuthorizationError",
    "ConstraintProvider",
    "ConstraintRegistry",
    "ConstraintConfig",
    "TimeConstraintConfig",
    "LocationConstraintConfig",
    "ResourceConstraintConfig",
    "ContextConstraintConfig",
    "ConstraintContext",
    "SubjectContext",
    "ResourceContext",
    "EnvironmentContext",
    "TimeConstraint",
    "LocationConstraint",
    "ResourceConstraint",
    "ContextConstraint",
    "require_permission",
    "require_role",
    "require_any_role",
    "require_all_roles",
    "business_hours_only",
    "weekday_only",
    "require_same_org",
    "cost_limit",
]
