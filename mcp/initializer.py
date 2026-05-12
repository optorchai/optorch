"""mcp package initializer"""
from optorch.logging import get_logger
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from optorch.config import ConfigManager
    from optorch.container import ApplicationContainer

logger = get_logger(__name__)


class McpPackageInitializer:
    """initializes mcp server registry and connections"""
    
    @staticmethod
    def initialize(
        config_manager: 'ConfigManager',
        container: Optional['ApplicationContainer'] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> None:
        """register mcp servers from config (sync registration only)
        
        actual connection happens async via connect()
        
        args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
            
        returns:
            None (servers registered in MCPRegistry)
        """
        from optorch.mcp import MCPRegistry, MCPConfig, MCPServerConfig
        from optorch.initializer_utils import extract_optorch_config
        
        if MCPRegistry._clients:
            logger.debug("MCP servers already registered")
            return
        
        config_manager.register_config("mcp", MCPConfig)
        logger.info("✅ mcp config model registered")
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        if overrides:
            mcp_dict = config_manager.merge_overrides("mcp", overrides, isolate=True)
        else:
            mcp_dict = optorch_config.get("mcp", {})
        
        if not mcp_dict:
            logger.warning("No MCP config - MCPs not available")
            return
        
        mcp_config = MCPConfig(**mcp_dict) if isinstance(mcp_dict, dict) else mcp_dict
        
        MCPRegistry.set_config(mcp_config)
        
        servers = mcp_config.servers
        if not servers:
            logger.warning("MCP config loaded but no servers defined")
            return
        
        for name, server_config in servers.items():
            if isinstance(server_config, dict):
                server = MCPServerConfig(**server_config)
            else:
                server = server_config
            MCPRegistry.register(name, server)
        
        logger.info(f"✅ MCP servers registered: {len(servers)} servers")
        
        optorch_config = config_manager.get("optorch", {})
        global_auto_discover = optorch_config.get("auto_discover", True)
        
        if mcp_dict is None or isinstance(mcp_dict, dict):
            package_auto_discover = (mcp_dict or {}).get("auto_discover", global_auto_discover)
        else:
            if "auto_discover" in mcp_dict.model_fields_set:
                package_auto_discover = mcp_dict.auto_discover
            else:
                package_auto_discover = global_auto_discover
        
        if package_auto_discover:
            McpPackageInitializer.discover(config_manager, container)
        else:
            logger.debug("mcp auto_discover disabled (global or package level) - manual tool registration required")
    
    @staticmethod
    def discover(
        config_manager: 'ConfigManager',
        container: Optional['ApplicationContainer'] = None,
        force: bool = False
    ) -> None:
        """discover and register app-defined tools (MCP server tools auto-discovered on connect)
        
        args:
            config_manager: ConfigManager with tools config
            container: ApplicationContainer with tool_registry
            force: if True, ignores auto_discover flags and always discovers
        """
        from optorch.loader import AutoLoader
        from optorch.mcp import MCPConfig
        
        if not container:
            logger.warning("no container - tools not discovered")
            return
        
        if hasattr(container, 'node_controller') and container.node_controller:
            tool_registry = container.node_controller.tools
        elif hasattr(container, 'tool_registry') and container.tool_registry:
            tool_registry = container.tool_registry
        else:
            logger.warning("no tool registry - tools not discovered")
            return
        
        mcp_config_dict = config_manager.get("mcp", {})
        if not mcp_config_dict:
            logger.debug("no mcp config - tools not discovered")
            return
        
        optorch_config = config_manager.get("optorch", {})
        global_auto_discover = optorch_config.get("auto_discover", True)
        mcp_config = MCPConfig(**mcp_config_dict) if isinstance(mcp_config_dict, dict) else mcp_config_dict
        package_auto_discover = mcp_config.auto_discover if mcp_config.auto_discover is not None else global_auto_discover
        
        if not force and not package_auto_discover:
            logger.debug("mcp auto_discover disabled (global or package level)")
            return
        
        if force or (package_auto_discover and mcp_config.tools.auto_discover):
            tools_config = config_manager.get("tools")
            if tools_config:
                AutoLoader.register(
                    tool_registry,
                    tools_config,
                    mcp_config.tools.module,
                    instantiate=mcp_config.tools.instantiate
                )
                logger.debug(f"discovered {len(tools_config)} app tools from {mcp_config.tools.module}")
    
    @staticmethod
    async def initialize_async(container: Optional[Any] = None) -> None:
        """async initialization - connect to mcp servers and discover tools"""
        await McpPackageInitializer.connect()
        
        if container and hasattr(container, 'tool_registry'):
            await McpPackageInitializer.register_tools(container)
        
        if container and hasattr(container, 'extension_registry'):
            from optorch.mcp import MCPRegistry
            container.extension_registry.register("mcp", cleanup=MCPRegistry.disconnect_all)
    
    @staticmethod
    async def connect() -> None:
        """connect to all registered mcp servers and discover their tools (async)
        
        called after sync initialization completes
        """
        from optorch.mcp import MCPRegistry
        
        try:
            await MCPRegistry.connect_all()
            
            tool_count = MCPRegistry.get_tool_count()
            logger.info(f"✅ MCP tool discovery complete: {tool_count} tools mapped")
            if tool_count > 0:
                logger.debug(f"Available MCP tools: {MCPRegistry.get_tool_names()}")
        except Exception as e:
            logger.warning(f"MCP connection failed: {e}")
    
    @staticmethod
    async def register_tools(container: Any) -> None:
        """auto-register MCP tools to ToolRegistry
        
        skips tools that already have manual proxies registered
        respects per-server/per-tool config overrides from mcp.yaml
        """
        from optorch.mcp import MCPRegistry
        
        if not hasattr(container, 'tool_registry'):
            logger.warning("No tool_registry in container - skipping MCP tool auto-registration")
            return
        
        mcp_config = container.config_manager.get("optorch.mcp", {})
        server_configs = mcp_config.get("servers", {})
        
        config_overrides = {}
        for server_name, server_cfg in server_configs.items():
            if "tools" in server_cfg:
                config_overrides[server_name] = {"tools": server_cfg["tools"]}
        
        try:
            registered = await MCPRegistry.discover_and_register_tools(container.tool_registry, config_overrides=config_overrides)
            
            if registered > 0:
                logger.info(f"✅ Auto-registered {registered} MCP tools")
        except Exception as e:
            logger.error(f"Failed to auto-register MCP tools: {e}", exc_info=True)
