from datetime import datetime, UTC
from typing import TYPE_CHECKING, List, Optional
from optorch.logging import get_logger
from optorch.identity.licensing.models import License, Constraint
from optorch.identity.authorization.models import Decision

if TYPE_CHECKING:
    from optorch.identity.config import LicenseConfig
    from optorch.identity.organization.manager import OrganizationManager
    from optorch.events.event_emitter import EventEmitter
    from optorch.storage.manager import StorageManager
    from optorch.identity.licensing.usage.manager import UsageManager

logger = get_logger(__name__)


class LicenseManager:
    """Manages license validation"""

    def __init__(
        self,
        config: "LicenseConfig",
        org_manager: "OrganizationManager",
        event_emitter: Optional["EventEmitter"] = None,
        storage_manager: Optional["StorageManager"] = None,
    ):
        self.config = config
        self.org_manager = org_manager
        self.event_emitter = event_emitter
        self.storage = storage_manager

        from optorch.identity.licensing.online_validator import OnlineValidator
        from optorch.identity.licensing.offline_validator import OfflineValidator
        from optorch.identity.licensing.usage import UsageManager, UsageTrackerRegistry, UsageTrackingListener

        self.online_validator = OnlineValidator(config)
        self.offline_validator = OfflineValidator(config)

        self.usage_manager: Optional["UsageManager"] = None
        self.usage_listener = None
        if config.usage_tracking.enabled:
            registry = UsageTrackerRegistry()
            self.usage_manager = UsageManager(config=config.usage_tracking, registry=registry, storage_manager=storage_manager)
            self.usage_listener = UsageTrackingListener(self.usage_manager)
            
            if event_emitter:
                event_emitter.register_listener(self.usage_listener)

    async def initialize(self) -> None:
        """async initialization for usage manager"""
        if self.usage_manager:
            await self.usage_manager.initialize()

    async def validate(
        self, license: License, action: str, context: dict
    ) -> Decision:
        """Validate license permits action (XACML-style decision)"""
        now = datetime.now(UTC)
        if now < license.valid_from or now > license.valid_until:
            if self.event_emitter:
                self.event_emitter.emit("license.denied", {
                    "license_id": license.uid,
                    "reason": "License expired or not yet valid",
                    "action": action,
                    "feature": context.get("feature")
                })
            return Decision(result="Deny", reason="License expired or not yet valid")

        feature = context.get("feature")
        for prohibition in license.prohibitions:
            if prohibition.target == feature and prohibition.action == action:
                if self.event_emitter:
                    self.event_emitter.emit("license.denied", {
                        "license_id": license.uid,
                        "reason": f"Feature {feature} prohibited",
                        "action": action,
                        "feature": feature
                    })
                return Decision(result="Deny", reason=f"Feature {feature} prohibited")

        for permission in license.permissions:
            if permission.target == feature and permission.action == action:
                constraint_result = await self._evaluate_constraints(permission.constraints, context, license.uid)

                if constraint_result.result == "Permit":
                    if self.event_emitter:
                        self.event_emitter.emit("license.validated", {
                            "license_id": license.uid,
                            "action": action,
                            "feature": feature
                        })
                    return Decision(result="Permit", reason=f"License permits {action} on {feature}")
                else:
                    if self.event_emitter:
                        self.event_emitter.emit("license.denied", {
                            "license_id": license.uid,
                            "reason": constraint_result.reason,
                            "action": action,
                            "feature": feature
                        })
                    return Decision(result="Deny", reason=constraint_result.reason)

        if self.event_emitter:
            self.event_emitter.emit("license.denied", {
                "license_id": license.uid,
                "reason": "No matching permission found",
                "action": action,
                "feature": feature
            })
        return Decision(result="Deny", reason="No matching permission found")

    async def _evaluate_constraints(
        self, constraints: List[Constraint], context: dict, license_id: Optional[str] = None
    ) -> Decision:
        """evaluate ODRL constraints including usage limits"""
        for constraint in constraints:
            if constraint.left_operand == "count":
                current_usage = 0
                if self.usage_manager and constraint.unit:
                    org_id = context.get("org_id", context.get("organization_id", ""))
                    
                    metric = constraint.unit
                    window = None
                    if "/" in constraint.unit:
                        parts = constraint.unit.split("/")
                        metric = parts[0]
                        window = parts[1] if len(parts) > 1 else None
                    
                    try:
                        current_usage = await self.usage_manager.get_usage(organization_id=org_id, metric=metric, window=window)
                    except Exception as e:
                        logger.error(f"Usage check failed for org={org_id} metric={metric}: {e}", exc_info=True)
                        return Decision(result="Deny", reason=f"Usage check unavailable for {metric}")

                limit = constraint.right_operand
                
                # quota warning at 90%
                if constraint.operator in ["lteq", "<="] and current_usage >= limit * 0.9:
                    if self.event_emitter:
                        self.event_emitter.emit("license.quota_warning", {
                            "license_id": license_id,
                            "metric": constraint.unit,
                            "current_usage": current_usage,
                            "limit": limit,
                            "percentage": (current_usage / limit * 100) if limit > 0 else 0
                        })

                if not self._check_operator(current_usage, constraint.operator, limit):
                    if self.event_emitter:
                        self.event_emitter.emit("license.quota_exceeded", {
                            "license_id": license_id,
                            "metric": constraint.unit,
                            "current_usage": current_usage,
                            "limit": limit
                        })
                    return Decision(result="Deny", reason=f"Usage limit exceeded: {current_usage}/{limit} {constraint.unit}")

            elif constraint.left_operand == "dateTime":
                pass

        return Decision(result="Permit", reason="All constraints satisfied")
    
    def _check_operator(self, left: int, operator: str, right: int) -> bool:
        """check constraint operator"""
        if operator in ["lteq", "<="]:
            return left <= right
        elif operator in ["gteq", ">="]:
            return left >= right
        elif operator in ["eq", "=="]:
            return left == right
        elif operator in ["neq", "!="]:
            return left != right
        elif operator in ["lt", "<"]:
            return left < right
        elif operator in ["gt", ">"]:
            return left > right
        return False

    def extract_entitlements(self, license: License) -> List[str]:
        """Extract feature entitlements from license"""
        entitlements = []

        for permission in license.permissions:
            entitlements.append(permission.target)

        return entitlements
