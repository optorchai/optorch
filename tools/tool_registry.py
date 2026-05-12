from typing import Any, Optional, TYPE_CHECKING
from optorch.registry import Registry
from optorch.tools.base_tool import BaseTool
from optorch.events import emits, EventTypes
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.controller.node_context import NodeContext

logger = get_logger(__name__)


class ToolRegistry(Registry[BaseTool]):
    
    def get(self, key: str) -> BaseTool:
        """override to provide better error message - lazy loading happens in execute()"""
        if key not in self._items:
            raise KeyError(f"Item not registered: {key}")
        return self._items[key]
    
    async def _async_lazy_get_mcp_tool(self, tool_name: str) -> BaseTool | None:
        """async lazy load MCP tools on demand - called from execute()"""
        from optorch.mcp import MCPRegistry
        from optorch.mcp.mcp_tool_adapter import MCPToolAdapter
        
        logger.info(f"Starting lazy load for tool: {tool_name}")
        logger.info(f"MCPRegistry has {len(MCPRegistry._clients)} clients, discovered={MCPRegistry._discovered}")
        logger.info(f"MCPRegistry tool_routing: {list(MCPRegistry._tool_routing.keys())}")
        
        tool_client = MCPRegistry.get_for_tool(tool_name)
        if not tool_client:
            logger.warning(f"No MCP client found for tool: {tool_name}")
            logger.info(f"Available MCP clients: {list(MCPRegistry._clients.keys())}")
            
            if MCPRegistry._clients and not MCPRegistry._discovered:
                logger.info("MCPRegistry not discovered yet, running discovery now")
                await MCPRegistry.discover()
                logger.info(f"After discovery: {len(MCPRegistry._tool_routing)} tools mapped")
                tool_client = MCPRegistry.get_for_tool(tool_name)
            
            if not tool_client:
                return None
        
        logger.info(f"Found MCP client '{tool_client.name}' for tool '{tool_name}'")
        
        try:
            if not tool_client.adapter.is_connected:
                logger.info(f"Connecting MCP client '{tool_client.name}' for lazy tool load")
                await tool_client.connect()
            else:
                logger.info(f"MCP client '{tool_client.name}' already connected")
            
            logger.info(f"Listing tools from MCP client '{tool_client.name}'")
            tools_list = await tool_client.list_tools()
            logger.info(f"Found {len(tools_list)} tools from MCP client '{tool_client.name}'")
            
            tool_metadata = None
            for t in tools_list:
                t_name = t.get("name") if isinstance(t, dict) else t
                if t_name == tool_name:
                    tool_metadata = t if isinstance(t, dict) else {"name": tool_name}
                    break
            
            if not tool_metadata:
                logger.warning(f"Tool '{tool_name}' not found in MCP server, using default metadata")
                tool_metadata = {"name": tool_name, "description": f"MCP tool: {tool_name}"}
            
            adapter = MCPToolAdapter(tool_name, tool_client, tool_metadata)
            self.register(tool_name, adapter)
            logger.info(f"✅ Lazy loaded MCP tool: {tool_name}")
            return adapter
        except Exception as e:
            logger.error(f"❌ Failed to lazy load tool {tool_name}: {e}", exc_info=True)
            return None
    
    @emits(EventTypes.TOOL)
    async def execute(self, *, tool_name: str, context: Optional['NodeContext'] = None, **kwargs: Any) -> Any:
        tool = self.get_optional(tool_name)
        
        if tool is None:
            logger.info(f"Tool '{tool_name}' not found, attempting lazy MCP load")
            tool = await self._async_lazy_get_mcp_tool(tool_name)
        
        if tool is None:
            raise KeyError(f"Item not registered: {tool_name}")
        
        schema = tool.get_schema()
        required_params = schema.get("parameters", {}).get("required", [])
        
        missing_params = [param for param in required_params if param not in kwargs or kwargs[param] is None]
        
        if missing_params:
            error_msg = (
                f"Error: Tool '{tool_name}' is missing required parameters: {', '.join(missing_params)}. "
                f"Please call the tool again with all required parameters included."
            )
            logger.warning(f"Tool execution blocked: {error_msg}")
            return {"error": error_msg, "missing_parameters": missing_params}
        
        return await tool.execute(**kwargs)
    
    def get_tool_schemas(self, tool_names: list[str] | None = None) -> list[dict[str, Any]]:
        if tool_names is None:
            tool_names = self.list_keys()
        
        schemas = []
        for name in tool_names:
            if not self.has(name):
                continue
            tool = self.get(name)
            schemas.append(tool.get_schema())
        return schemas
