"""MCP Registry - manages multiple MCP client instances"""
import asyncio
from optorch.logging import get_logger
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING
from .mcp_client import MCPClient
from .mcp_config import MCPServerConfig, MCPConfig

if TYPE_CHECKING:
    from optorch.tools.tool_registry import ToolRegistry

logger = get_logger(__name__)


class MCPRegistry:
    """Registry for managing multiple MCP clients"""
    
    _clients: Dict[str, MCPClient] = {}
    _tool_routing: Dict[str, str] = {}
    _discovered: bool = False
    _lock: asyncio.Lock = asyncio.Lock()
    _config: Optional[MCPConfig] = None
    
    @classmethod
    def set_config(cls, config: MCPConfig) -> None:
        """set MCP configuration"""
        cls._config = config
        logger.debug(f"MCP config set: auto_connect={config.auto_connect}")
    
    @classmethod
    def register(cls, name: str, config: MCPServerConfig) -> None:
        """Register a new MCP server
        
        Args:
            name: Unique identifier for this MCP
            config: Pydantic MCPServerConfig instance
        """
        if not config.enabled:
            logger.info(f"Skipping disabled MCP: {name}")
            return
        
        client = MCPClient(name, config)
        cls._clients[name] = client
        logger.info(f"Registered MCP client '{name}' ({config.transport} transport) -> {config.url}")
    
    @classmethod
    def get(cls, name: str) -> Optional[MCPClient]:
        """Get MCP client by name"""
        return cls._clients.get(name)
    
    @classmethod
    def get_default(cls) -> Optional[MCPClient]:
        """Get first available MCP client"""
        return next(iter(cls._clients.values()), None) if cls._clients else None
    
    @classmethod
    async def discover(cls) -> None:
        """Discover tools from all registered MCPs and build routing map"""
        if cls._discovered:
            return
        
        async with cls._lock:
            if cls._discovered:
                return
            
            logger.info("Discovering tools from MCPs...")
            for name, client in cls._clients.items():
                try:
                    logger.info(f"Querying tools from '{name}' at {client.config.url}")
                    tools = await client.list_tools()
                    for tool in tools:
                        tool_name = tool.get("name") if isinstance(tool, dict) else tool
                        if tool_name:
                            cls._tool_routing[tool_name] = name
                            logger.info(f"Mapped tool '{tool_name}' -> '{name}'")
                    logger.info(f"Discovered {len(tools)} tools from '{name}'")
                except Exception as e:
                    logger.error(f"Failed to discover tools from '{name}' at {client.config.url}: {e}")
            
            cls._discovered = True
            logger.info(f"Tool discovery complete: {len(cls._tool_routing)} tools mapped")
    
    @classmethod
    def get_for_tool(cls, tool_name: str) -> Optional[MCPClient]:
        if not cls._discovered and cls._clients:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    logger.debug("Tool discovery not complete, using first available MCP")
                    return cls.get_default()
                else:
                    loop.run_until_complete(cls.discover())
            except RuntimeError:
                asyncio.run(cls.discover())
        
        mcp_name = cls._tool_routing.get(tool_name)
        if mcp_name:
            return cls._clients.get(mcp_name)
        return cls.get_default()
    
    @classmethod
    def list(cls) -> List[str]:
        """List all registered MCP clients"""
        return list(cls._clients.keys())
    
    @classmethod
    def has_clients(cls) -> bool:
        """Check if any clients are registered"""
        return bool(cls._clients)
    
    @classmethod
    def get_tool_count(cls) -> int:
        """Get count of discovered tools"""
        return len(cls._tool_routing)
    
    @classmethod
    def get_tool_names(cls) -> List[str]:
        """Get list of all discovered tool names"""
        return list(cls._tool_routing.keys())
    
    @classmethod
    def get_server_tool_count(cls, server_name: str) -> int:
        """Get count of tools for specific server"""
        return sum(1 for route_name in cls._tool_routing.values() if route_name == server_name)
    
    @classmethod
    async def connect_all(cls):
        """Connect to all enabled MCP servers with retry logic"""
        if not cls._clients:
            logger.debug("No MCP servers registered")
            return
        
        if not cls._config:
            logger.warning("No MCP config set - using defaults")
            auto_connect = True
            retry_attempts = 3
            retry_delay = 2
        else:
            auto_connect = cls._config.auto_connect
            retry_attempts = cls._config.retry_attempts
            retry_delay = cls._config.retry_delay
        
        if not auto_connect:
            logger.info("auto_connect disabled - skipping MCP connections")
            return
        
        logger.debug(f"Connecting to {len(cls._clients)} MCP server(s)...")
        for name, client in cls._clients.items():
            if not client.config.enabled:
                continue
            
            for attempt in range(retry_attempts):
                try:
                    logger.info(f"Connecting to '{name}' at {client.config.url} ({client.config.transport}) - attempt {attempt + 1}/{retry_attempts}")
                    await client.connect()
                    logger.info(f"Successfully connected to '{name}'")
                    break
                except Exception as e:
                    if attempt < retry_attempts - 1:
                        delay = retry_delay * (2 ** attempt)
                        logger.warning(f"Connection to '{name}' failed: {e} - retrying in {delay}s")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"Failed to connect to '{name}' after {retry_attempts} attempts: {e}")
    
    @classmethod
    async def close_all(cls):
        """Close all MCP connections"""
        for name, client in cls._clients.items():
            try:
                await client.close()
                logger.debug(f"Closed MCP client: {name}")
            except Exception as e:
                logger.warning(f"Error closing MCP client {name}: {e}")
    
    @classmethod
    async def disconnect_all(cls):
        """Disconnect all MCP clients and clear registry"""
        await cls.close_all()
        cls._clients.clear()
        cls._tool_routing.clear()
        cls._discovered = False
        logger.info("All MCP clients disconnected")
    
    @classmethod
    async def discover_and_register_tools(cls, tool_registry: 'ToolRegistry', config_overrides: Optional[Dict[str, Any]] = None) -> int:
        """discover MCP tools and auto-register to ToolRegistry
        
        Args:
            tool_registry: ToolRegistry instance to register tools to
            config_overrides: Optional per-server tool config (from mcp.yaml)
        
        Returns:
            number of tools registered
        
        Example config_overrides:
            {
                "tavily": {
                    "tools": {
                        "search_web": {"enabled": False},  # skip this tool
                        "other_tool": {"wrapper": "app.wrappers.custom_wrapper"}
                    }
                }
            }
        """
        from optorch.mcp.mcp_tool_adapter import MCPToolAdapter
        
        if not cls._discovered:
            await cls.discover()
        
        registered_count = 0
        config_overrides = config_overrides or {}
        
        for mcp_name, client in cls._clients.items():
            try:
                logger.debug(f"Discovering tools from '{mcp_name}'...")
                tools = await client.list_tools()
                
                server_config = config_overrides.get(mcp_name, {})
                tool_configs = server_config.get("tools", {})
                
                for tool_meta in tools:
                    tool_name = tool_meta.get("name") if isinstance(tool_meta, dict) else tool_meta
                    if not tool_name:
                        continue
                    
                    tool_cfg = tool_configs.get(tool_name, {})
                    if tool_cfg.get("enabled") is False:
                        logger.debug(f"Tool '{tool_name}' disabled via config, skipping")
                        continue
                    
                    if tool_registry.has(tool_name):
                        logger.debug(f"Tool '{tool_name}' already registered (manual proxy), skipping auto-registration")
                        continue
                    
                    wrapper_fn = None
                    if wrapper_path := tool_cfg.get("wrapper"):
                        try:
                            wrapper_fn = cls._load_wrapper(wrapper_path)
                        except Exception as e:
                            logger.warning(f"Failed to load wrapper '{wrapper_path}' for tool '{tool_name}': {e}")
                    
                    adapter = MCPToolAdapter(
                        tool_name=tool_name,
                        mcp_client=client,
                        tool_metadata=tool_meta if isinstance(tool_meta, dict) else {"name": tool_name},
                        wrapper_fn=wrapper_fn
                    )
                    
                    tool_registry.register(tool_name, adapter)
                    registered_count += 1
                    logger.debug(f"Auto-registered MCP tool: {tool_name} (server: {mcp_name})")
                
                logger.info(f"Registered {registered_count} tools from '{mcp_name}'")
                
            except Exception as e:
                logger.error(f"Failed to discover tools from '{mcp_name}': {e}")
        
        logger.info(f"✅ MCP tool auto-registration complete: {registered_count} tools")
        return registered_count
    
    @classmethod
    def _load_wrapper(cls, wrapper_path: str) -> Callable[..., Any]:
        """load custom wrapper function from module path
        
        Args:
            wrapper_path: e.g. "app.wrappers.custom_wrapper" or "app.wrappers.MyClass.method"
        """
        import importlib
        
        parts = wrapper_path.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid wrapper path: {wrapper_path}")
        
        module_path, attr_name = parts
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
