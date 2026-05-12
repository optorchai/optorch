"""Event system constants and enums"""
from enum import IntEnum


class Priority(IntEnum):
    """Listener execution priority - lower number = higher priority"""
    CRITICAL = 0
    HIGH = 10
    NORMAL = 50
    LOW = 100


class ListenerTags:
    """Standard listener tags for routing"""
    EXECUTION = "execution"
    OBSERVABILITY = "observability"
    METRICS = "metrics"
    CRITICAL = "critical"
    BROADCAST = "broadcast"
