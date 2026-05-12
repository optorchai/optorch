"""Authorization manager"""

from typing import Any, Dict, Optional, TYPE_CHECKING, Literal

from optorch.identity.authorization.models import Decision
from optorch.identity.authorization.provider import AuthorizationProvider
from optorch.identity.audit import AuditLogger

if TYPE_CHECKING:
    from optorch.events.event_emitter import EventEmitter
    from optorch.storage.manager import StorageManager
    from extensions.interact.manager import InteractionManager


class AuthorizationManager:
    """Manages authorization operations"""

    def __init__(
        self, 
        provider: AuthorizationProvider, 
        event_emitter: Optional["EventEmitter"] = None,
        storage_manager: Optional["StorageManager"] = None,
        enable_audit_logging: bool = True,
        interaction_manager: Optional["InteractionManager"] = None,
        enable_interactive_enforcement: bool = False,
        interactive_risk_threshold: Literal["low", "medium", "high", "critical"] = "high"
    ):
        self.provider = provider
        self.event_emitter = event_emitter
        self.audit_logger = AuditLogger(storage_manager=storage_manager, enabled=enable_audit_logging)
        self.interaction_manager = interaction_manager
        self.enable_interactive_enforcement = enable_interactive_enforcement
        self.interactive_risk_threshold = interactive_risk_threshold

    async def check_permission(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        environment: Dict[str, Any] | None = None,
    ) -> Decision:
        """Check if subject has permission to perform action on resource"""
        if self.event_emitter:
            self.event_emitter.emit("authorization.policy_evaluated", {
                "subject_id": subject.get("id"),
                "resource": resource,
                "action": action
            })
        
        decision = await self.provider.check_permission(subject, resource, action, environment)
        
        subject_id = subject.get("id", str(subject))
        resource_str = resource.get("id") if isinstance(resource, dict) else str(resource)
        await self.audit_logger.log_authorization(
            subject=subject_id,
            resource=resource_str or "unknown",
            action=action,
            decision=decision.result,
            provider=self.provider.__class__.__name__,
            reason=decision.reason or ""
        )
        
        if self.event_emitter:
            if decision.result == "Permit":
                self.event_emitter.emit("authorization.permit", {
                    "subject_id": subject.get("id"),
                    "resource": resource,
                    "action": action,
                    "reason": decision.reason
                })
            else:
                self.event_emitter.emit("authorization.deny", {
                    "subject_id": subject.get("id"),
                    "resource": resource,
                    "action": action,
                    "reason": decision.reason
                })
        
        return decision

    async def check_permission_with_enforcement(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        environment: Dict[str, Any] | None = None,
        enforcement: Literal["block", "interactive", "warn"] = "block",
        risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    ) -> Decision:
        """check permission with enforcement strategy
        
        enforcement strategies:
        - block: raise error on deny (default)
        - interactive: show approval form, wait for human decision
        - warn: log warning but allow access
        """
        decision = await self.check_permission(subject, resource, action, environment)
        
        if decision.result == "Permit":
            return decision
        
        if enforcement == "interactive" and self.enable_interactive_enforcement:
            return await self._handle_interactive_enforcement(
                subject=subject,
                resource=resource,
                action=action,
                decision=decision,
                risk_level=risk_level
            )
        elif enforcement == "warn":
            return self._handle_warn_enforcement(subject, resource, action, decision)
        else:  # block
            return decision  # caller handles Deny result
    
    async def _handle_interactive_enforcement(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        decision: Decision,
        risk_level: str
    ) -> Decision:
        """trigger approval workflow for denied permissions"""
        if not self.interaction_manager:
            return decision  # no interaction manager, return original deny
        
        subject_id = subject.get("id", str(subject))
        resource_id = resource.get("id") if isinstance(resource, dict) else str(resource)
        
        if not self._should_trigger_approval(risk_level):
            return decision  # below threshold, deny normally
        
        from optorch.logging import get_logger
        import time
        logger = get_logger(__name__)
        
        interaction_id = f"authz_{subject_id}_{resource_id}_{action}_{int(time.time())}"
        logger.info(f"interactive enforcement triggered: {subject_id} -> {resource_id}:{action} (risk={risk_level})")
        
        try:
            approval_response = await self.interaction_manager.request_interaction(
                interaction_id=interaction_id,
                timeout=600,  # 10 min default
                node_name="authorization_approval"
            )
            
            if not approval_response:
                logger.warning(f"approval timeout: {interaction_id}")
                await self.audit_logger.log_authorization(
                    subject=subject_id,
                    resource=resource_id or "unknown",
                    action=action,
                    decision="deny",
                    provider="interactive_enforcement",
                    reason="approval timeout"
                )
                return decision  # timeout, return original deny
            
            approved = approval_response.get("approved", False)
            justification = approval_response.get("justification", "")
            
            if approved:
                logger.info(f"access approved: {subject_id} -> {resource_id}:{action}")
                await self.audit_logger.log_authorization(
                    subject=subject_id,
                    resource=resource_id or "unknown",
                    action=action,
                    decision="permit",
                    provider="interactive_enforcement",
                    reason=f"manual approval: {justification}"
                )
                return Decision(result="Permit", reason=f"approved by human: {justification}")
            else:
                logger.info(f"access rejected: {subject_id} -> {resource_id}:{action}")
                await self.audit_logger.log_authorization(
                    subject=subject_id,
                    resource=resource_id or "unknown",
                    action=action,
                    decision="deny",
                    provider="interactive_enforcement",
                    reason=f"manual rejection: {justification}"
                )
                return Decision(result="Deny", reason=f"rejected by human: {justification}")
        
        except Exception as e:
            logger.error(f"interactive enforcement failed: {e}", exc_info=True)
            return decision  # fallback to original deny
    
    def _handle_warn_enforcement(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        decision: Decision
    ) -> Decision:
        """log warning but convert deny to permit"""
        from optorch.logging import get_logger
        logger = get_logger(__name__)
        
        subject_id = subject.get("id", str(subject))
        resource_id = resource.get("id") if isinstance(resource, dict) else str(resource)
        
        logger.warning(
            f"permission denied but allowing access (warn enforcement): "
            f"{subject_id} -> {resource_id}:{action} | reason: {decision.reason}"
        )
        
        return Decision(result="Permit", reason=f"warn enforcement: {decision.reason}")
    
    def _should_trigger_approval(self, risk_level: str) -> bool:
        """check if risk level meets threshold for approval"""
        risk_order = ["low", "medium", "high", "critical"]
        threshold_idx = risk_order.index(self.interactive_risk_threshold)
        risk_idx = risk_order.index(risk_level)
        return risk_idx >= threshold_idx

    async def add_policy(self, policy: Dict[str, Any]) -> None:
        """Add authorization policy"""
        await self.provider.add_policy(policy)
        
        policy_id = policy.get("id", "unknown")
        await self.audit_logger.log_policy_change(
            subject="system",
            action="policy_created",
            policy_id=policy_id,
            after=policy,
            reason="policy added to authorization system"
        )

    async def remove_policy(self, policy_id: str) -> None:
        """Remove authorization policy"""
        policies = await self.provider.list_policies()
        before = next((p for p in policies if p.get("id") == policy_id), None)
        
        await self.provider.remove_policy(policy_id)
        
        await self.audit_logger.log_policy_change(
            subject="system",
            action="policy_deleted",
            policy_id=policy_id,
            before=before,
            reason="policy removed from authorization system"
        )

    async def list_policies(self) -> list[Dict[str, Any]]:
        """List all policies"""
        return await self.provider.list_policies()

    async def list_roles(self) -> list[str]:
        """List all available roles"""
        return await self.provider.list_roles()
