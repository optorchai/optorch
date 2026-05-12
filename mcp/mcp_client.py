"""MCP Client - handles connection and communication with a single MCP server"""
from optorch.logging import get_logger
from typing import Any, Dict, List
from .mcp_config import MCPServerConfig
from .adapters import MCPTransportAdapter, AdapterRegistry

logger = get_logger(__name__)


class MCPClient:
    """Client for a single MCP server"""
    
    def __init__(self, name: str, config: MCPServerConfig) -> None:
        self.name = name
        self.config = config
        self.adapter = self._create_adapter()
    
    def _create_adapter(self) -> MCPTransportAdapter:
        """Create appropriate transport adapter based on config"""
        adapter_class = AdapterRegistry.get(self.config.transport)
        return adapter_class(self.config)
    
    async def connect(self) -> bool:
        """Establish connection """
        try:
            connected = await self.adapter.connect()
            if connected:
                logger.info(f"Connected to MCP '{self.name}' via {self.config.transport}")
            return connected
        except Exception as e:
            logger.error(f"MCP connection error [{self.name}]: {e}")
            return False
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool"""
        logger.info(f"Calling MCP tool '{tool_name}' on '{self.name}'")
        return await self.adapter.call(tool_name, params)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        return await self.adapter.list()
    
    async def close(self) -> None:
        """Close the MCP connection"""
        await self.adapter.close()
