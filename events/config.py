"""events package config"""
from typing import Dict, Any
from pydantic import BaseModel, Field


class EventDistributionConfig(BaseModel):
    """event distribution strategy"""
    type: str = Field(
        default="tag_based",
        description="Event routing strategy (tag_based, broadcast, or custom)"
    )


class EventsConfig(BaseModel):
    """event system config"""
    distribution: EventDistributionConfig = Field(
        default_factory=EventDistributionConfig,
        description="Event routing strategy"
    )
    listeners: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event listener configurations"
    )
    backends: Dict[str, Any] = Field(
        default_factory=lambda: {"local": {"enabled": True, "type": "local"}},
        description="Event backend configs (timescaledb, etc)"
    )
