"""MCP Client Provider"""
import inspect
from optorch.logging import get_logger
from typing import Any, Dict, Optional
from .mcp_registry import MCPRegistry
from .mcp_client import MCPClient

logger = get_logger(__name__)


class MCPClientProvider:
    def __init__(self, mcp_name: Optional[str] = None) -> None:
        self.mcp_name = mcp_name
        self._client: Optional[MCPClient] = None
    
    @property
    def client(self) -> MCPClient:
        if self._client is not None:
            return self._client
            
        if self.mcp_name:
            self._client = MCPRegistry.get(self.mcp_name)
            if not self._client:
                raise ValueError(f"MCP client '{self.mcp_name}' not registered")
        else:
            tool_name = self._get_calling_tool_name()
            if tool_name:
                self._client = MCPRegistry.get_for_tool(tool_name)
            else:
                self._client = MCPRegistry.get_default()
            
        if not self._client:
            raise ValueError("No MCP client available")
        
        return self._client
    
    def _get_calling_tool_name(self) -> Optional[str]:
        try:
            for frame_info in inspect.stack()[2:]:
                func_name = frame_info.function
                if not func_name.startswith('_') and func_name not in ['wrapper', 'execute']:
                    return func_name
        except Exception:
            pass
        return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.call_tool(tool_name, arguments)
