"""enforcement strategies for protection manager - XACML 3.0 PEP pattern"""

from typing import Protocol, Optional, TYPE_CHECKING
from pydantic import BaseModel
from optorch.registry import Registry
from optorch.errors import AuthorizationError
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.identity.protection.config import ProtectionConfig

logger = get_logger(__name__)


class EnforcementResult(BaseModel):
    """result of enforcement strategy"""
    allowed: bool
    action: Optional[str] = None  # "raise" | "route" | "interact" | "warn"
    route_to: Optional[str] = None  # if action="route"
    form: Optional[dict] = None  # if action="interact"
    warning: Optional[str] = None  # if action="warn"


class EnforcementStrategy(Protocol):
    """strategy for handling permission denials"""

    async def enforce(
        self,
        protection: "ProtectionConfig",
        decision: bool,
    ) -> EnforcementResult:
        """handle permission check result"""
        ...


class BlockEnforcement:
    """raise AuthorizationError on denial - default enforcement"""

    async def enforce(
        self,
        protection: "ProtectionConfig",
        decision: bool,
    ) -> EnforcementResult:
        if not decision:
            raise AuthorizationError(
                f"Permission denied: {protection.permission}",
                resource=protection.resource_type,
                action=protection.action,
                details={
                    "resource_id": protection.resource_id,
                    "permission": protection.permission,
                    "enforcement": "block",
                },
            )
        return EnforcementResult(allowed=True)


class InteractiveEnforcement:
    """show approval form on denial - for approval workflows"""

    async def enforce(
        self,
        protection: "ProtectionConfig",
        decision: bool,
    ) -> EnforcementResult:
        if not decision:
            return EnforcementResult(
                allowed=False,
                action="interact",
                form={
                    "type": "permission_approval",
                    "resource": protection.resource_id,
                    "action": protection.action,
                    "approver_role": protection.approver_role,
                    "description": protection.description,
                },
            )
        return EnforcementResult(allowed=True)


class RouteEnforcement:
    """route to fallback on denial - for conditional flows"""

    async def enforce(
        self,
        protection: "ProtectionConfig",
        decision: bool,
    ) -> EnforcementResult:
        if not decision:
            if not protection.fallback:
                logger.warning(
                    f"route enforcement requires fallback, but none configured for {protection.resource_id}"
                )
                raise AuthorizationError(
                    f"Permission denied: {protection.permission}",
                    resource=protection.resource_type,
                    action=protection.action,
                )

            return EnforcementResult(allowed=False, action="route", route_to=protection.fallback)
        return EnforcementResult(allowed=True)


class WarnEnforcement:
    """log warning but allow access - for development/monitoring"""

    async def enforce(
        self,
        protection: "ProtectionConfig",
        decision: bool,
    ) -> EnforcementResult:
        if not decision:
            warning_msg = (
                f"permission denied but allowing access: {protection.permission} "
                f"for {protection.resource_type}:{protection.resource_id}"
            )
            logger.warning(warning_msg)

            return EnforcementResult(allowed=True, action="warn", warning=warning_msg)
        return EnforcementResult(allowed=True)


class EnforcementRegistry(Registry[EnforcementStrategy]):
    """registry of enforcement strategies"""

    def __init__(self):
        super().__init__()
        self._register_builtins()

    def _register_builtins(self) -> None:
        """register framework enforcement strategies"""
        self.register("block", BlockEnforcement())
        self.register("interactive", InteractiveEnforcement())
        self.register("route", RouteEnforcement())
        self.register("warn", WarnEnforcement())

        logger.debug("registered builtin enforcement strategies: block, interactive, route, warn")

    def get_strategy(self, name: str) -> EnforcementStrategy:
        """get enforcement strategy by name, fallback to block"""
        strategy = self.get_optional(name)
        if not strategy:
            logger.warning(
                f"unknown enforcement strategy: {name}, falling back to 'block'"
            )
            return self.get("block")
        return strategy
