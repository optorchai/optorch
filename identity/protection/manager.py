"""protection manager - policy enforcement point (PEP)"""

from typing import Optional, TYPE_CHECKING
from optorch.identity.protection.registry import ProtectionRegistry
from optorch.identity.protection.enforcement import (
    EnforcementRegistry,
    EnforcementResult,
)
from optorch.logging import get_logger
from optorch.errors import AuthorizationError

if TYPE_CHECKING:
    from optorch.identity.manager import IdentityManager

logger = get_logger(__name__)


class ProtectionManager:
    """policy enforcement point - wraps identity checks with resource metadata
    
    XACML 3.0 PEP pattern - looks up required permissions and enforces them
    """

    def __init__(
        self,
        identity: "IdentityManager",
        registry: Optional[ProtectionRegistry] = None,
        enforcement: Optional[EnforcementRegistry] = None,
    ):
        """initialize protection manager
        
        Args:
            identity: identity manager (PDP)
            registry: protection registry (PIP) - optional, created if not provided
            enforcement: enforcement registry - optional, created if not provided
        """
        self.identity = identity
        self.registry = registry or ProtectionRegistry()
        self.enforcement = enforcement or EnforcementRegistry()

    async def check(
        self,
        resource_type: str,
        resource_id: str,
        action: str,
        user: Optional[dict] = None,
    ) -> EnforcementResult:
        """check if user can perform action on resource with enforcement
        
        Args:
            resource_type: type of resource (config, tool, route, etc.)
            resource_id: specific resource identifier
            action: action to perform (read, update, execute, etc.)
            user: user dict (optional - uses current user from context)
        
        Returns:
            enforcement result (allowed, action, route_to, form, warning)
        """
        protection = self.registry.get_protection(resource_type, resource_id, action)

        if not protection:
            logger.debug(f"{resource_type}:{resource_id}:{action} not protected - allowing")
            return EnforcementResult(allowed=True)

        resource, perm_action = self._parse_permission(protection.permission)
        decision = await self.identity.check_permission(resource=resource, action=perm_action or action, user=user)

        logger.debug(
            f"protection check {resource_type}:{resource_id}:{action} -> "
            f"{protection.permission} = {decision}"
        )

        strategy = self.enforcement.get_strategy(protection.enforcement)
        result = await strategy.enforce(protection=protection, decision=decision)
        return result

    async def require(
        self,
        resource_type: str,
        resource_id: str,
        action: str,
        user: Optional[dict] = None,
    ) -> EnforcementResult:
        """require permission - enforces via strategy
        
        Args:
            resource_type: type of resource
            resource_id: specific resource identifier
            action: action to perform
            user: user dict (optional)
        
        Returns:
            enforcement result
        
        Raises:
            AuthorizationError: if enforcement strategy is 'block' and denied
        """
        result = await self.check(resource_type, resource_id, action, user)

        if not result.allowed and result.action == "raise":
            raise AuthorizationError(
                f"Permission denied: {action} on {resource_type}:{resource_id}",
                resource=resource_type,
                action=action,
            )

        return result

    async def get_accessible_resources(
        self,
        resource_type: str,
        action: str,
        user: Optional[dict] = None,
    ) -> list[str]:
        """get all resources of type that user can perform action on
        
        Args:
            resource_type: type of resource
            action: action to check
            user: user dict (optional)
        
        Returns:
            list of resource_ids user can access
        """
        protections = self.registry.list_by_type(resource_type)
        accessible = []

        for protection in protections:
            if protection.action != action:
                continue

            resource, perm_action = self._parse_permission(protection.permission)
            decision = await self.identity.check_permission(resource=resource, action=perm_action or action, user=user)

            if decision:
                accessible.append(protection.resource_id)

        logger.debug(f"found {len(accessible)}/{len(protections)} accessible {resource_type} resources for action {action}")

        return accessible

    def _parse_permission(self, permission: str) -> tuple[str, Optional[str]]:
        """parse permission string into resource and action
        
        Args:
            permission: permission string like "config:secrets:update" or "tool:execute"
        
        Returns:
            (resource, action) tuple - action may be None if not in permission string
        """
        parts = permission.split(":")
        if len(parts) >= 3:
            return ":".join(parts[:-1]), parts[-1]
        elif len(parts) == 2:
            return parts[0], parts[1]
        else:
            return permission, None
