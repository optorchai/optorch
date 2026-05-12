"""controller configuration models"""

from pydantic import BaseModel, Field
from optorch.config.path_config import PathConfig


class DiscoveryPathsConfig(BaseModel):
    """controller-specific discovery paths (nodes + intents + tools)"""
    nodes: PathConfig = Field(
        default_factory=lambda: PathConfig(module="", auto_discover=True, instantiate=False),
        description="node discovery config"
    )
    intents: PathConfig = Field(
        default_factory=lambda: PathConfig(module="", auto_discover=True, instantiate=True),
        description="intent discovery config"
    )
    tools: PathConfig = Field(
        default_factory=lambda: PathConfig(module="", auto_discover=True, instantiate=False),
        description="tool discovery config"
    )


class ControllerConfig(BaseModel):
    """node controller configuration"""
    auto_discover: bool | None = Field(default=None, description="enable automatic component discovery from config")
    discovery_paths: DiscoveryPathsConfig = Field(default_factory=DiscoveryPathsConfig, description="module paths for discovery")
    
    model_config = {"extra": "allow"}
