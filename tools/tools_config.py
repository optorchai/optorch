"""native tool configuration model"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    """per-tool config for native tools"""
    
    enabled: bool = Field(
        default=True,
        description="whether tool is enabled"
    )
    
    timeout: Optional[float] = Field(
        default=None,
        description="execution timeout in seconds"
    )
    
    retries: Optional[int] = Field(
        default=None,
        description="retry attempts on failure"
    )
    
    model_config = {"extra": "allow"}


class ToolsConfig(BaseModel):
    """registry of native tool configurations - dynamic tool names"""
    
    __pydantic_extra__: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = {"extra": "allow"}
