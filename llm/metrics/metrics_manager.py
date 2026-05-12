"""Central metrics collection and aggregation"""
from optorch.logging import get_logger
from typing import Dict, Any, List, Optional
from collections import defaultdict
from optorch.llm.metrics.types import MetricType
from optorch.llm.metrics.usage import Usage

logger = get_logger(__name__)

class MetricsManager:
    """Central metrics collection point - simple in-memory for now"""
    
    _metrics: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    _enabled_types: set[str] = {MetricType.USAGE}
    
    @classmethod
    def configure(cls, config: Dict[str, Any]) -> None:
        """Configure metrics section"""
        enabled = config.get("enabled_types", ["usage"])
        cls._enabled_types = set(enabled)
        logger.info(f"Metrics enabled: {cls._enabled_types}")
    
    @classmethod
    def record(cls, session_id: str, metric_type: str, data: Dict[str, Any]) -> None:
        """Record a metric"""
        if metric_type not in cls._enabled_types:
            return
        
        cls._metrics[session_id][metric_type].append(data)
    
    @classmethod
    def record_usage(cls, session_id: str, usage: Usage) -> None:
        """Convenience method for usage tracking"""
        cls.record(session_id, MetricType.USAGE, usage.to_dict())
    
    @classmethod
    def get_stats(cls, session_id: str, metric_type: Optional[str] = None) -> Dict[str, Any]:
        """Get stats for session - aggregate if metric_type specified"""
        if session_id not in cls._metrics:
            return {}
        
        if metric_type:
            metrics = cls._metrics[session_id].get(metric_type, [])
            if metric_type == MetricType.USAGE:
                return cls._aggregate_usage(metrics)
            return {"metrics": metrics}
        
        return dict(cls._metrics[session_id])
    
    @classmethod
    def _aggregate_usage(cls, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate usage metrics"""
        if not metrics:
            return {"total_input": 0, "total_output": 0, "total_cost": 0.0}
        
        return {
            "total_input": sum(m.get("input_tokens", 0) for m in metrics),
            "total_output": sum(m.get("output_tokens", 0) for m in metrics),
            "total_tokens": sum(m.get("total_tokens", 0) for m in metrics),
            "total_cost": sum(m.get("cost", 0.0) for m in metrics),
            "currency": metrics[0].get("currency", "usd"),
            "request_count": len(metrics)
        }
    
    @classmethod
    def clear_session(cls, session_id: str) -> None:
        """Clear metrics for session"""
        if session_id in cls._metrics:
            del cls._metrics[session_id]
