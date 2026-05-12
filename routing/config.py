"""routing configuration"""

from pydantic import BaseModel, Field
from typing import Optional


class RoutingConfig(BaseModel):
    """orchestrator routing configuration"""
    default_node: Optional[str] = Field(
        default=None,
        description="default entry node when not specified in Orchestrator.create_async(entry_node=...)"
    )
    
    model_config = {"extra": "forbid"}
