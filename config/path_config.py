"""PathConfig model for component discovery configuration"""
from pydantic import BaseModel, Field


class PathConfig(BaseModel):
    """configuration for component discovery from a module path"""
    module: str = Field(description="module path for discovery (e.g. 'app.nodes')")
    auto_discover: bool = Field(default=True, description="enable auto-discovery for this component type")
    instantiate: bool = Field(default=False, description="instantiate classes on registration")
