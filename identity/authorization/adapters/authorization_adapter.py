"""authorization adapter for interactive enforcement"""

import time
import asyncio
from pydantic import BaseModel, Field
from typing import Type, TYPE_CHECKING, Literal, Optional, Dict, Any
from optorch.logging import get_logger
from optorch.identity.authorization.approval_form import AuthorizationApprovalForm

if TYPE_CHECKING:
    from optorch.identity.authorization.manager import AuthorizationManager
    from extensions.interact.manager import InteractionManager

logger = get_logger(__name__)


class AuthorizationAdapterConfig(BaseModel):
    """authorization adapter configuration"""
    timeout: int = Field(default=600, description="approval timeout in seconds")
    layout: str = Field(default="modal", description="ui layout for approval form")
    ui_schema: dict = Field(default_factory=dict, description="custom ui schema overrides")
    risk_threshold: Literal["low", "medium", "high", "critical"] = Field(
        default="medium",
        description="minimum risk level requiring approval"
    )


class AuthorizationAdapter:
    """interactive authorization enforcement
    
    triggers manual approval for high-risk authorization decisions
    integrates with interact extension's AdapterRegistry
    """

    name = "authorization"

    def __init__(
        self,
        interaction_manager: "InteractionManager",
        authz_manager: Optional["AuthorizationManager"] = None,
        config: Optional[AuthorizationAdapterConfig] = None
    ):
        self.interaction_manager = interaction_manager
        self.authz_manager = authz_manager
        cfg = config or AuthorizationAdapterConfig()
        self._timeout = cfg.timeout
        self._layout = cfg.layout
        self._ui_schema = cfg.ui_schema
        self.risk_threshold = cfg.risk_threshold
    
    @property
    def form_model(self) -> Type[BaseModel]:
        """pydantic model for approval form"""
        return AuthorizationApprovalForm
    
    def get_ui_schema(self) -> dict:
        """custom ui schema for form rendering"""
        base_schema = {
            "ui:order": ["subject", "resource", "action", "justification", "risk_level", "duration"],
            "justification": {
                "ui:widget": "textarea",
                "ui:placeholder": "Explain why this access is needed..."
            },
            "risk_level": {
                "ui:widget": "radio"
            },
            "duration": {
                "ui:help": "Leave empty for permanent access"
            }
        }
        base_schema.update(self._ui_schema)
        return base_schema
    
    def should_trigger(self, subject: str, resource: str, action: str, risk_level: str) -> bool:
        """check if approval needed based on risk"""
        risk_order = ["low", "medium", "high", "critical"]
        threshold_idx = risk_order.index(self.risk_threshold)
        risk_idx = risk_order.index(risk_level)
        
        return risk_idx >= threshold_idx
    
    async def request_approval(
        self,
        subject: str,
        resource: str,
        action: str,
        risk_level: str = "medium",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """request manual approval for authorization decision
        
        returns approval response with approved boolean and justification
        """
        
        if not self.should_trigger(subject, resource, action, risk_level):
            return {"approved": True, "reason": "below risk threshold"}
        
        interaction_id = f"authz_{subject}_{resource}_{action}_{int(time.time())}"
        logger.info(f"authorization approval requested: {subject} -> {resource}:{action} (id={interaction_id})")
        
        try:
            result = await self.interaction_manager.request_interaction(
                interaction_id=interaction_id,
                timeout=self._timeout,
                node_name="authorization_approval"
            )
            
            if not result:
                logger.warning(f"authorization approval timeout: {interaction_id}")
                return {"approved": False, "reason": "approval timeout"}
            
            approved = result.get("approved", False)
            justification = result.get("justification", "")
            
            if not approved:
                logger.info(f"authorization denied by approver: {subject} -> {resource}:{action}")
                return {"approved": False, "reason": f"rejected: {justification}"}
            
            logger.info(f"authorization approved: {subject} -> {resource}:{action}")
            
            # handle temporary access
            if result.get("duration") and self.authz_manager:
                await self._grant_temporary_access(subject, resource, action, result["duration"])
            
            return {"approved": True, "reason": f"approved: {justification}", "duration": result.get("duration")}
            
        except Exception as e:
            logger.error(f"authorization approval failed: {e}", exc_info=True)
            return {"approved": False, "reason": f"error: {str(e)}"}
    
    async def _grant_temporary_access(
        self,
        subject: str,
        resource: str,
        action: str,
        duration: int
    ) -> None:
        """grant time-limited access via temporary policy"""
        if not self.authz_manager:
            logger.warning("cannot grant temporary access: no authz_manager")
            return
        
        policy_id = f"temp_{subject}_{resource}_{action}_{int(time.time())}"
        policy = {
            "id": policy_id,
            "subject": subject,
            "resource": resource,
            "action": action,
            "effect": "allow",
            "temporary": True,
            "expires_at": int(time.time() + duration)
        }
        
        await self.authz_manager.add_policy(policy)
        logger.info(f"temporary access granted: {subject} -> {resource}:{action} for {duration}s (policy_id={policy_id})")
        
        # schedule revocation
        async def revoke_access():
            await asyncio.sleep(duration)
            if not self.authz_manager:
                logger.warning("cannot revoke temporary access: no authz_manager")
                return
            try:
                await self.authz_manager.remove_policy(policy_id)
                logger.info(f"temporary access revoked: {subject} -> {resource}:{action}")
            except Exception as e:
                logger.error(f"failed to revoke temporary access: {e}")
        
        asyncio.create_task(revoke_access())
