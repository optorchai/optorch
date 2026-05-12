"""Metrics types and base classes"""
from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, Any

class MetricType(str, Enum):
    """Types of metrics tracked"""
    USAGE = "usage"
    # LATENCY = "latency"
    # ERROR = "error"
    # CACHE_HIT = "cache_hit"


class BaseMetric(ABC):
    """Base class for all metric types"""
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict"""
        pass
