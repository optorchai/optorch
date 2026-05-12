"""Node configuration models"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class DeploymentConfig(BaseModel):
    """Node deployment configuration"""
    mode: str = Field(default="local", description="local or distributed")
    queue: Optional[str] = Field(default=None, description="kafka queue for distributed mode")
    timeout: float = Field(default=60.0, description="rpc timeout seconds")


class RoutingConfig(BaseModel):
    """Node routing configuration"""
    model_config = {"extra": "allow"}
    
    default: Optional[str] = Field(default=None, description="default next node")
    calls: List[str] = Field(default_factory=list, description="nodes this node can route to")
    conditions: Optional[List[Dict[str, Any]]] = Field(default=None, description="conditional routing rules")
    on: Optional[Dict[str, str]] = Field(default=None, description="event-based routing")
    type: Optional[str] = Field(default=None, description="routing type")
    field: Optional[str] = Field(default=None, description="field for conditional routing")


class IntentsConfig(BaseModel):
    """Node intent hooks configuration"""
    pre_dispatch: List[str] = Field(default_factory=list)
    post_dispatch: List[str] = Field(default_factory=list)
    pre_execute: List[str] = Field(default_factory=list)
    post_execute: List[str] = Field(default_factory=list)


class PromptsConfig(BaseModel):
    """Node prompts configuration"""
    model_config = {"extra": "allow"}
    
    system: Optional[str] = None
    user: Optional[str] = None
    inline: Optional[Dict[str, str]] = None


class NodeConfig(BaseModel):
    """
    Complete node configuration with validation
    
    validates structure from YAML config
    allows extension-specific fields (budget, interactions, etc.) via extra="allow"
    """
    model_config = {"extra": "allow"}
    
    # core
    class_name: Optional[str] = Field(default=None, alias="class", description="node class name")
    type: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    phase: Optional[str] = None
    
    # execution
    llm: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    streaming: bool = False
    
    # routing
    routing: Optional[RoutingConfig] = Field(default_factory=RoutingConfig)
    
    # intents
    intents: Optional[IntentsConfig] = Field(default_factory=IntentsConfig)
    
    # prompts
    prompts: Optional[PromptsConfig] = Field(default_factory=PromptsConfig)
    
    # deployment (enterprise extension)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    
    # extensions can add their own fields:
    # budget: Dict[str, Any] (budget extension)
    # interactions: Dict[str, Any] (interact extension)
    # suggestions: bool (interact extension)
    
    # metrics
    execution_order: Optional[int] = None
    parent_nodes: List[str] = Field(default_factory=list)
