"""webhook registry for auth events"""

import logging
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, UTC, UTC

logger = logging.getLogger(__name__)


class WebhookRegistry:
    """manage webhooks for authentication/authorization events
    
    features:
    - event-based subscriptions
    - payload formatting with context injection
    - delivery retry with exponential backoff
    - async delivery (non-blocking)
    """

    def __init__(self):
        self.webhooks: Dict[str, List[Dict[str, Any]]] = {}
        self.client = httpx.AsyncClient(timeout=10.0)
        self.max_retries = 3
        self.retry_backoff = 1.0  # seconds
    
    def register(
        self,
        event_type: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        formatter: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    ) -> None:
        """register webhook for event type
        
        event_type examples:
        - auth.login.success
        - auth.login.failure
        - auth.token.issued
        - authz.decision.deny
        - authz.approval.required
        """
        if event_type not in self.webhooks:
            self.webhooks[event_type] = []
        
        self.webhooks[event_type].append({
            "url": url,
            "headers": headers or {},
            "formatter": formatter
        })
        
        logger.info(f"registered webhook: {event_type} -> {url}")
    
    def unregister(self, event_type: str, url: str) -> None:
        """remove webhook subscription"""
        if event_type in self.webhooks:
            self.webhooks[event_type] = [w for w in self.webhooks[event_type] if w["url"] != url]
    
    async def dispatch(self, event_type: str, payload: Dict[str, Any]) -> None:
        """send webhook for event (async, non-blocking)"""
        
        if event_type not in self.webhooks:
            return
        
        asyncio.create_task(self._deliver_all(event_type, payload))
    
    async def _deliver_all(self, event_type: str, payload: Dict[str, Any]) -> None:
        """deliver to all subscribers"""
        
        tasks = []
        for webhook in self.webhooks[event_type]:
            task = self._deliver_one(webhook, event_type, payload)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _deliver_one(
        self,
        webhook: Dict[str, Any],
        event_type: str,
        payload: Dict[str, Any]
    ) -> None:
        """deliver to single webhook with retry"""
        
        url = webhook["url"]
        headers = webhook["headers"]
        formatter = webhook["formatter"]
        
        if formatter:
            formatted_payload = formatter(payload)
        else:
            formatted_payload = self._default_format(event_type, payload)
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(url, json=formatted_payload, headers=headers)
                response.raise_for_status()
                logger.info(f"webhook delivered: {event_type} -> {url}")
                return
                
            except Exception as e:
                last_error = e
                logger.warning(f"webhook delivery failed (attempt {attempt + 1}): {url} - {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_backoff * (2 ** attempt))
        
        logger.error(f"webhook delivery failed after {self.max_retries} attempts: {url} - {last_error}")
    
    def _default_format(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """default payload format with context injection"""
        return {
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": payload,
            "version": "1.0"
        }
    
    async def close(self) -> None:
        """cleanup http client"""
        await self.client.aclose()
