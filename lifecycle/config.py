"""lifecycle configuration models"""

from pydantic import BaseModel, Field
from typing import Optional


class LifecycleHookConfig(BaseModel):
    """single lifecycle hook"""
    name: str = Field(description="hook name (pre_dispatch, post_dispatch, etc)")
    enabled: bool = Field(default=True, description="whether hook is active")
    execute_intents: bool = Field(
        default=False,
        description="execute intent handlers during this hook"
    )
    core_intents: list[str] = Field(
        default=[],
        description="core intent names to execute"
    )
    node_method: Optional[str] = Field(
        default=None,
        description="node method to call (e.g. pre_execute)"
    )


class LifecycleConfig(BaseModel):
    """lifecycle hooks configuration"""
    hooks: list[LifecycleHookConfig] = Field(
        default=[],
        description="list of lifecycle hooks"
    )
