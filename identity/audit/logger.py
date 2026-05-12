"""centralized audit logging service"""

from typing import Optional, Any, Dict, TYPE_CHECKING
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = get_logger(__name__)


class AuditLogger:
    """audit logging manager for identity operations
    
    logs authentication, authorization, and policy change events
    for compliance, security monitoring, and debugging
    """
    
    def __init__(self, storage_manager: Optional["StorageManager"] = None, enabled: bool = True):
        self.storage = storage_manager
        self.enabled = enabled
    
    async def log_authentication(
        self,
        subject: str,
        action: str,
        decision: str,
        provider: str = "",
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """log authentication event (login, logout, token operations)
        
        Args:
            subject: user identifier
            action: login, logout, token_issued, token_refreshed, token_revoked
            decision: success or failure
            provider: authentication provider name
            reason: success/failure reason
            metadata: additional context (ip, user_agent, etc)
        """
        if not self.enabled or not self.storage:
            return
        
        resource = metadata.get("resource", "authentication") if metadata else "authentication"
        await self._write_audit_log(
            subject=subject,
            resource=resource,
            action=action,
            decision=decision,
            provider=provider,
            reason=reason
        )
    
    async def log_authorization(
        self,
        subject: str,
        resource: str,
        action: str,
        decision: str,
        provider: str = "",
        reason: str = ""
    ) -> None:
        """log authorization decision
        
        Args:
            subject: user/entity identifier
            resource: resource being accessed
            action: action being performed (read, write, delete, etc)
            decision: permit or deny
            provider: authorization provider name
            reason: policy evaluation reason
        """
        if not self.enabled or not self.storage:
            return
        
        await self._write_audit_log(
            subject=subject,
            resource=resource,
            action=action,
            decision=decision.lower(),
            provider=provider,
            reason=reason
        )
    
    async def log_policy_change(
        self,
        subject: str,
        action: str,
        policy_id: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        reason: str = ""
    ) -> None:
        """log policy modification
        
        Args:
            subject: user making the change
            action: policy_created, policy_updated, policy_deleted
            policy_id: policy identifier
            before: previous policy state (for updates/deletes)
            after: new policy state (for creates/updates)
            reason: change justification
        """
        if not self.enabled or not self.storage:
            return
        
        # serialize before/after for reason field
        change_details = reason
        if before or after:
            parts = []
            if before:
                parts.append(f"before={before}")
            if after:
                parts.append(f"after={after}")
            change_details = f"{reason} | {' | '.join(parts)}" if reason else ' | '.join(parts)
        
        await self._write_audit_log(
            subject=subject,
            resource=f"policy:{policy_id}",
            action=action,
            decision="success",
            provider="policy_management",
            reason=change_details[:500]  # truncate long policy diffs
        )
    
    async def _write_audit_log(
        self,
        subject: str,
        resource: str,
        action: str,
        decision: str,
        provider: str,
        reason: str
    ) -> None:
        """write audit log entry via storage query"""
        if not self.storage:
            return
        
        try:
            await self.storage.query(
                "identity.create_audit_log",
                subject=subject,
                resource=resource,
                action=action,
                decision=decision,
                provider=provider,
                reason=reason
            )
        except Exception as e:
            logger.error(f"audit log write failed: {e}", exc_info=True)
