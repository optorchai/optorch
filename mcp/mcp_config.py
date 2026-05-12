"""MCP configuration models"""
from typing import Literal, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_serializer
from optorch.config.path_config import PathConfig
from optorch.utils.env_resolver import resolve_env_or_value


class MCPToolConfig(BaseModel):
    """per-tool configuration for MCP tools"""
    
    enabled: bool = Field(
        default=True,
        description="whether this tool is enabled (false = skip auto-registration)"
    )
    
    wrapper: Optional[str] = Field(
        default=None,
        description="custom wrapper function path (e.g. 'app.wrappers.custom_fn')"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="custom metadata for UI display"
    )
    
    model_config = {"extra": "allow"}


class MCPServerConfig(BaseModel):
    """individual MCP server configuration"""
    
    url: str = Field(
        description="MCP server URL"
    )
    
    transport: Literal['http', 'sse'] = Field(
        default='sse',
        description="transport protocol"
    )
    
    timeout: int = Field(
        default=30,
        description="connection timeout in seconds"
    )
    
    enabled: bool = Field(
        default=True,
        description="whether this MCP is enabled"
    )
    
    auth_type: Optional[Literal['none', 'bearer', 'api_key', 'basic']] = Field(
        default=None,
        description="authentication type"
    )
    
    auth_token: Optional[str] = Field(
        default=None,
        description="auth token/api key (resolved from env if ${VAR})"
    )
    
    auth_header: Optional[str] = Field(
        default=None,
        description="custom auth header name (defaults: Bearer=Authorization, api_key=X-API-Key)"
    )
    
    tools: Dict[str, MCPToolConfig] = Field(
        default_factory=dict,
        description="per-tool configuration overrides"
    )
    
    http_call_endpoint: str = Field(
        default='/call',
        description="HTTP call endpoint path"
    )
    
    http_list_endpoint: str = Field(
        default='/tools',
        description="HTTP list tools endpoint path"
    )
    
    sse_call_method: str = Field(
        default='tools/call',
        description="SSE call method name"
    )
    
    sse_list_method: str = Field(
        default='tools/list',
        description="SSE list tools method name"
    )
    
    @field_validator('url', 'auth_token')
    @classmethod
    def resolve_url(cls, v: str) -> str:
        """resolve url from env var if needed"""
        return resolve_env_or_value(v) if v else v
    
    model_config = {"extra": "allow"}


class MCPConfig(BaseModel):
    """MCP system configuration with optorch defaults"""
    
    servers: Dict[str, MCPServerConfig] = Field(
        default_factory=dict,
        description="MCP servers by name"
    )
    
    auto_discover: bool | None = Field(
        default=None,
        description="enable tool auto-discovery from MCP servers"
    )
    
    tools: PathConfig = Field(
        default_factory=lambda: PathConfig(module="app.tools", auto_discover=True, instantiate=False),
        description="tool discovery config (for app-defined tools, MCP tools auto-discovered from servers)"
    )
    
    auto_connect: bool = Field(
        default=False,
        description="auto-connect to all enabled MCPs on startup"
    )
    
    retry_attempts: int = Field(
        default=3,
        description="connection retries with exponential backoff"
    )
    
    retry_delay: int = Field(
        default=2,
        description="initial delay in seconds (doubles each retry)"
    )
    
    keepalive: bool = Field(
        default=True,
        description="maintain persistent connections"
    )
    
    reconnect_on_timeout: bool = Field(
        default=True,
        description="auto-reconnect on SSE timeout"
    )
    
    @field_validator('servers', mode='before')
    @classmethod
    def filter_all_key(cls, v: Any) -> Any:
        """filter out 'all' and 'Native' keys - used for global/native tool config, not servers"""
        if isinstance(v, dict):
            filtered = {k: val for k, val in v.items() if k not in ('all', 'Native')}
            return filtered
        return v
    
    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        """ensure reserved keys stay filtered on serialization"""
        return {
            'servers': {k: v for k, v in self.servers.items() if k not in ('all', 'Native')}
        }
    
    model_config = {"extra": "allow"}
