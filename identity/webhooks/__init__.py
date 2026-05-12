"""webhook init"""

from optorch.identity.webhooks.registry import WebhookRegistry
from optorch.identity.webhooks.listener import WebhookEventListener

__all__ = ["WebhookRegistry", "WebhookEventListener"]
