"""webhook event listener - bridges event emitter to webhook registry"""

from typing import TYPE_CHECKING, Any, Dict
from optorch.logging import get_logger
from optorch.events.listeners.base import BaseListener
import asyncio

if TYPE_CHECKING:
    from optorch.identity.webhooks.registry import WebhookRegistry

logger = get_logger(__name__)


class WebhookEventListener(BaseListener):
    """listen to identity events and dispatch webhooks
    
    subscribes to all auth/authz events and triggers registered webhooks
    """
    
    def __init__(self, webhook_registry: "WebhookRegistry"):
        super().__init__()
        self.webhook_registry = webhook_registry
        self.event_mappings = {
            "authentication.success": "auth.login.success",
            "authentication.failed": "auth.login.failure",
            "authentication.rate_limited": "auth.rate_limited",
            "authentication.provider_failed": "auth.provider.failed",
            "authentication.fallback_success": "auth.fallback.success",
            "authentication.provider_tried": "auth.provider.tried",
            
            "authorization.permit": "authz.decision.permit",
            "authorization.deny": "authz.decision.deny",
            "authorization.policy_evaluated": "authz.policy.evaluated",
            
            "license.validated": "license.validated",
            "license.denied": "license.denied",
            "license.quota_warning": "license.quota.warning",
            "license.quota_exceeded": "license.quota.exceeded",
        }
    
    def on_event(self, event: Dict[str, Any]) -> None:
        """BaseListener callback - dispatch to webhook registry
        
        Args:
            event: Event dict with type, data, timestamp, etc.
        """
        event_type = event.get("type")
        if not event_type or not isinstance(event_type, str):
            return
        
        data = event.get("data", {})
        
        webhook_event = self.event_mappings.get(event_type)
        if not webhook_event:
            return
        
        payload = data.copy()
        if "context" in event:
            payload['context'] = event['context']
        
        logger.debug(f"dispatching webhook: {webhook_event}")
        
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.webhook_registry.dispatch(webhook_event, payload))
        except RuntimeError:
            logger.warning(f"no event loop for webhook dispatch: {webhook_event}")
    
    def register_with_emitter(self, event_emitter: Any) -> None:
        """register listener with event emitter for all identity events
        
        Args:
            event_emitter: EventEmitter instance to subscribe to
        """
        event_emitter.listeners.add(listener=self, priority=0, tags={"webhooks", "identity"})
        
        logger.info(f"webhook listener registered for {len(self.event_mappings)} event types")
