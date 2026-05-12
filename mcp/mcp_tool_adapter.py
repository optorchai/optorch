"""MCP tool adapter - wraps MCP tools as BaseTool instances"""
from typing import Any, Dict, Optional, Callable, TYPE_CHECKING
from optorch.tools.base_tool import BaseTool
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.mcp.mcp_client import MCPClient

logger = get_logger(__name__)


class MCPToolAdapter(BaseTool):
    """adapter to expose MCP tools through optorch ToolRegistry
    
    auto-generates tool from MCP metadata, no manual proxy needed
    """
    
    def __init__(
        self,
        tool_name: str,
        mcp_client: 'MCPClient',
        tool_metadata: Dict[str, Any],
        wrapper_fn: Optional[Callable[..., Any]] = None
    ) -> None:
        """
        Args:
            tool_name: Tool identifier
            mcp_client: MCPClient instance for calling tool
            tool_metadata: MCP tool schema/description
            wrapper_fn: Optional custom wrapper function for parameter/result transformation
        """
        self._name = tool_name
        self._mcp_client = mcp_client
        self._metadata = tool_metadata
        self._wrapper_fn = wrapper_fn
        self._description = tool_metadata.get("description", f"MCP tool: {tool_name}")
        self._parameters = tool_metadata.get("inputSchema", {})
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """convert MCP inputSchema to tool schema format"""
        return {
            "type": "object",
            "properties": self._parameters.get("properties", {}),
            "required": self._parameters.get("required", [])
        }
    
    async def execute(self, **kwargs: Any) -> Any:
        """execute MCP tool via client"""
        try:
            if self._wrapper_fn:
                return await self._wrapper_fn(self._mcp_client, self._name, kwargs)
            
            result = await self._mcp_client.call_tool(self._name, kwargs)
            
            if isinstance(result, dict):
                return {"success": True, **result}
            else:
                return {"success": True, "result": result}
                
        except Exception as e:
            logger.error(f"MCP tool '{self._name}' error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_metadata(self) -> Dict[str, Any]:
        """expose full MCP metadata for UI introspection"""
        return {
            "name": self._name,
            "description": self._description,
            "mcp_server": self._mcp_client.name,
            "transport": self._mcp_client.config.transport,
            "schema": self._metadata,
            "has_wrapper": self._wrapper_fn is not None
        }
