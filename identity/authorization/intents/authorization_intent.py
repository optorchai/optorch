"""authorization intent - PRE_EXECUTE node access control"""

from typing import Any, TYPE_CHECKING, Literal, cast
from optorch.logging import get_logger
from optorch.intents.base_intent_handler import BaseIntentHandler
from optorch.intents.intent_context import IntentContext
from optorch.identity.authorization.models import Decision

if TYPE_CHECKING:
    from optorch.identity.authorization.manager import AuthorizationManager

logger = get_logger(__name__)


class AuthorizationIntent(BaseIntentHandler):
    """check node access permissions before execution
    
    runs at PRE_EXECUTE lifecycle hook
    delegates to AuthorizationManager.check_permission_with_enforcement()
    """
    
    def __init__(
        self, 
        authz_manager: "AuthorizationManager",
        enabled: bool = True,
        default_enforcement: Literal["block", "interactive", "warn"] = "block",
        default_risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    ):
        self.authz_manager = authz_manager
        self.enabled = enabled
        self.default_enforcement = default_enforcement
        self.default_risk_level = default_risk_level
    
    async def execute(self, context: IntentContext) -> dict[str, Any]:
        """check node access permission"""
        if not self.enabled:
            logger.debug("authorization intent disabled - skipping")
            return {"authorized": True, "action": "continue"}
        
        subject = self._get_subject(context)
        if not subject:
            logger.debug("no subject in context - skipping authorization check")
            return {"authorized": True, "action": "continue"}
        
        resource = self._build_resource(context)
        action = self._get_action(context)
        enforcement_raw = getattr(context.node, 'authorization_enforcement', self.default_enforcement)
        risk_level_raw = getattr(context.node, 'authorization_risk_level', self.default_risk_level)
        enforcement = cast(Literal["block", "interactive", "warn"], enforcement_raw if enforcement_raw in ("block", "interactive", "warn") else self.default_enforcement)
        risk_level = cast(Literal["low", "medium", "high", "critical"], risk_level_raw if risk_level_raw in ("low", "medium", "high", "critical") else self.default_risk_level)
        
        logger.debug(
            f"checking authorization: subject={subject.get('id')} "
            f"resource={resource.get('id')} action={action} "
            f"enforcement={enforcement} risk={risk_level}"
        )
        
        decision: Decision = await self.authz_manager.check_permission_with_enforcement(
            subject=subject,
            resource=resource,
            action=action,
            environment=self._get_environment(context),
            enforcement=enforcement,
            risk_level=risk_level
        )
        
        if decision.result == "Permit":
            logger.info(f"access granted: {subject.get('id')} -> {resource.get('id')}:{action}")
            return {
                "authorized": True,
                "action": "continue",
                "decision": decision.result,
                "reason": decision.reason
            }
        else:
            logger.warning(
                f"access denied: {subject.get('id')} -> {resource.get('id')}:{action} | "
                f"reason: {decision.reason}"
            )
            return {
                "authorized": False,
                "action": "block",
                "decision": decision.result,
                "reason": decision.reason or "permission denied"
            }
    
    def _get_subject(self, context: IntentContext) -> dict[str, Any] | None:
        """extract subject from context state"""

        state = getattr(context, 'state', None)
        if state:
            subject_id = state.get('user_id') or state.get('subject_id')
            if subject_id:
                return {
                    "id": subject_id,
                    "type": state.get('user_type', 'user'),
                    "tenant": state.get('tenant_id'),
                    "roles": state.get('user_roles', [])
                }
        
        if node_subject := getattr(context.node, 'subject', None):
            return node_subject
        
        return None
    
    def _build_resource(self, context: IntentContext) -> dict[str, Any]:
        """build resource identifier from node"""
        node_name = getattr(context.node, 'name', str(context.node))
        
        resource = {
            "id": node_name,
            "type": "node",
            "node_name": node_name
        }
        
        if auth_resource := getattr(context.node, 'authorization_resource', None):
            resource.update(auth_resource)
        
        return resource
    
    def _get_action(self, context: IntentContext) -> str:
        """determine action from context"""
        return getattr(context.node, 'authorization_action', 'execute')
    
    def _get_environment(self, context: IntentContext) -> dict[str, Any]:
        """build environment context for policy evaluation"""
        import time
        
        env = {
            "timestamp": int(time.time()),
            "hook": "PRE_EXECUTE"
        }
        
        state = getattr(context, 'state', None)
        if state:
            if tenant := state.get('tenant_id'):
                env['tenant'] = tenant
            
            if session := state.get('session_id'):
                env['session'] = session
        
        if auth_env := getattr(context.node, 'authorization_environment', None):
            env.update(auth_env)
        
        return env
