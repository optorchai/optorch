"""usage tracking event listener - auto-increment on workflow/tool execution"""

from typing import Dict, Any, TYPE_CHECKING
from optorch.events.listeners.base import BaseListener
from optorch.constants import EventTypes
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.identity.licensing.usage.manager import UsageManager

logger = get_logger(__name__)


class UsageTrackingListener(BaseListener):
    """auto-increment usage counters on workflow/tool events
    
    tracks:
    - workflow executions
    - tool calls
    - API requests
    - LLM calls
    """
    
    def __init__(self, usage_manager: "UsageManager"):
        super().__init__()
        self.usage_manager = usage_manager
        self.needs_initialization = False
    
    def on_event(self, event: Dict[str, Any]):
        """increment usage counters based on event type"""
        event_type = event.get("type", "")
        
        org_id = self._get_org_id(event)
        if not org_id:
            return
        
        if event_type == f"{EventTypes.NODE}.complete":
            self._track_node_execution(event, org_id)
        elif event_type == f"{EventTypes.TOOL}.complete":
            self._track_tool_execution(event, org_id)
        elif event_type == f"{EventTypes.LLM}.complete":
            self._track_llm_call(event, org_id)
        elif event_type == "api.request" or event_type == "http.request":
            self._track_api_call(event, org_id)
    
    def _get_org_id(self, event: Dict[str, Any]) -> str | None:
        """extract organization_id from event context"""

        org_id = (
            event.get("organization_id") or
            event.get("org_id") or
            event.get("context", {}).get("organization_id") or
            event.get("context", {}).get("org_id") or
            event.get("state", {}).get("organization_id")
        )
        
        if not org_id:
            logger.debug(f"no org_id found in event type={event.get('type')}")
        
        return org_id
    
    def _track_node_execution(self, event: Dict[str, Any], org_id: str):
        """track node/workflow execution"""
        node_name = event.get("node_name", "unknown")
        
        try:
            import asyncio
            asyncio.create_task(
                self.usage_manager.track(
                    organization_id=org_id,
                    metric="workflow_executions",
                    amount=1,
                    window="monthly"
                )
            )
            logger.debug(f"tracked workflow execution: {node_name} for org={org_id}")
        except Exception as e:
            logger.error(f"failed to track workflow execution: {e}")
    
    def _track_tool_execution(self, event: Dict[str, Any], org_id: str):
        """track tool call"""
        tool_name = event.get("args", {}).get("tool_name", "unknown")
        
        try:
            import asyncio
            asyncio.create_task(
                self.usage_manager.track(
                    organization_id=org_id,
                    metric="tool_calls",
                    amount=1,
                    window="monthly"
                )
            )
            logger.debug(f"tracked tool call: {tool_name} for org={org_id}")
        except Exception as e:
            logger.error(f"failed to track tool call: {e}")
    
    def _track_llm_call(self, event: Dict[str, Any], org_id: str):
        """track LLM API call"""
        model = event.get("model", "unknown")
        
        try:
            import asyncio
            
            asyncio.create_task(
                self.usage_manager.track(
                    organization_id=org_id,
                    metric="llm_calls",
                    amount=1,
                    window="monthly"
                )
            )
            
            input_tokens = event.get("input_tokens", 0)
            output_tokens = event.get("output_tokens", 0)
            
            if input_tokens or output_tokens:
                asyncio.create_task(
                    self.usage_manager.track(
                        organization_id=org_id,
                        metric="llm_tokens",
                        amount=input_tokens + output_tokens,
                        window="monthly"
                    )
                )
            
            logger.debug(f"tracked LLM call: {model} for org={org_id}")
        except Exception as e:
            logger.error(f"failed to track LLM call: {e}")
    
    def _track_api_call(self, event: Dict[str, Any], org_id: str):
        """track API/HTTP request"""
        endpoint = event.get("endpoint", "unknown")
        
        try:
            import asyncio
            asyncio.create_task(
                self.usage_manager.track(
                    organization_id=org_id,
                    metric="api_calls",
                    amount=1,
                    window="monthly"
                )
            )
            logger.debug(f"tracked API call: {endpoint} for org={org_id}")
        except Exception as e:
            logger.error(f"failed to track API call: {e}")
