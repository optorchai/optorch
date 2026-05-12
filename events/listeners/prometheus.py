from typing import Dict, Any
from .base import BaseListener
from optorch.prometheus.registry import MetricsRegistry
from optorch.constants import EventTypes
from optorch.llm.pricing import Pricing


class PrometheusListener(BaseListener):
    """comprehensive metrics tracking via MetricsRegistry"""
    
    def __init__(self) -> None:
        super().__init__()
        self.metrics = MetricsRegistry()
    
    def on_event(self, event: Dict[str, Any]):
        event_type = event.get("type", "")
        
        # llm events
        if event_type == f"{EventTypes.LLM}.complete":
            self._handle_llm_complete(event)
        elif event_type == f"{EventTypes.LLM}.error":
            self._handle_llm_error(event)
        
        # tool events
        elif event_type == f"{EventTypes.TOOL}.complete":
            self._handle_tool_complete(event)
        elif event_type == f"{EventTypes.TOOL}.error":
            self._handle_tool_error(event)
        
        # node events
        elif event_type == f"{EventTypes.NODE}.complete":
            self._handle_node_complete(event)
        elif event_type == f"{EventTypes.NODE}.error":
            self._handle_node_error(event)
    
    def _handle_llm_complete(self, event: Dict[str, Any]):
        provider = event.get("provider", "unknown")
        model = event.get("model", "unknown")
        duration_ms = event.get("duration_ms", 0)
        
        usage = event.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost = usage.get("cost", 0.0)
        currency = usage.get("currency") or Pricing.get_currency()
        
        # record metrics
        self.metrics.llm_requests_total.labels(provider=provider, model=model, status="success").inc()
        self.metrics.llm_tokens_total.labels(provider=provider, model=model, token_type="prompt").inc(prompt_tokens)
        self.metrics.llm_tokens_total.labels(provider=provider, model=model, token_type="completion").inc(completion_tokens)
        self.metrics.llm_request_duration_seconds.labels(provider=provider, model=model).observe(duration_ms / 1000)
        
        if cost:
            self.metrics.llm_cost_total.labels(provider=provider, model=model, currency=currency).inc(cost)
    
    def _handle_llm_error(self, event: Dict[str, Any]):
        provider = event.get("provider", "unknown")
        model = event.get("model", "unknown")
        self.metrics.llm_requests_total.labels(provider=provider, model=model, status="error").inc()
    
    def _handle_tool_complete(self, event: Dict[str, Any]):
        tool_name = event.get("tool_name", "unknown")
        duration_ms = event.get("duration_ms", 0)
        
        self.metrics.tool_calls_total.labels(tool_name=tool_name, status="success").inc()
        self.metrics.tool_duration_seconds.labels(tool_name=tool_name).observe(duration_ms / 1000)
    
    def _handle_tool_error(self, event: Dict[str, Any]):
        tool_name = event.get("tool_name", "unknown")
        self.metrics.tool_calls_total.labels(tool_name=tool_name, status="error").inc()
    
    def _handle_node_complete(self, event: Dict[str, Any]):
        node = event.get("node", "unknown")
        duration_ms = event.get("duration_ms", 0)
        
        self.metrics.node_executions_total.labels(node_name=node, status="success").inc()
        self.metrics.node_duration_seconds.labels(node_name=node).observe(duration_ms / 1000)
    
    def _handle_node_error(self, event: Dict[str, Any]):
        node = event.get("node", "unknown")
        self.metrics.node_executions_total.labels(node_name=node, status="error").inc()
    
    def get_metrics(self) -> Dict[str, Any]:
        """basic metrics dict for API endpoint - aggregates across all labels"""
        llm_total = sum(m._value.get() for m in self.metrics.llm_requests_total._metrics.values()) if hasattr(self.metrics.llm_requests_total, '_metrics') else 0
        tool_total = sum(m._value.get() for m in self.metrics.tool_calls_total._metrics.values()) if hasattr(self.metrics.tool_calls_total, '_metrics') else 0
        node_total = sum(m._value.get() for m in self.metrics.node_executions_total._metrics.values()) if hasattr(self.metrics.node_executions_total, '_metrics') else 0
        
        return {
            "llm_calls": int(llm_total),
            "tool_calls": int(tool_total),
            "node_executions": int(node_total)
        }
