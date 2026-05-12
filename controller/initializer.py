"""controller package initializer"""

from optorch.logging import get_logger
from typing import TYPE_CHECKING, Dict, Any, Optional
from optorch.config import ConfigManager

if TYPE_CHECKING:
    from optorch.container import ApplicationContainer

logger = get_logger(__name__)

class ControllerPackageInitializer:
    """self-contained node controller initialization"""
    
    @staticmethod
    def initialize(
        config_manager: ConfigManager,
        container: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """initialize node controller and ensure dependencies exist
        
        args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
            
        returns:
            NodeController instance or None
        """
        from optorch.controller.node_controller import NodeController
        from optorch.controller.config import ControllerConfig
        from optorch.initializer_utils import extract_optorch_config
        
        if not container:
            logger.warning("No container provided - node controller not initialized")
            return None
        
        if hasattr(container, 'node_controller') and container.node_controller:
            logger.debug("node controller already initialized - skipping")
            return container.node_controller
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        config_manager.register_config("controller", ControllerConfig)
        logger.info("✅ controller config model registered")
        
        if overrides:
            controller_dict = config_manager.merge_overrides("controller", overrides, isolate=True)
            optorch_config["controller"] = controller_dict
        
        if not hasattr(container, 'lifecycle_executor') or container.lifecycle_executor is None:
            from optorch.lifecycle.initializer import LifecyclePackageInitializer
            LifecyclePackageInitializer.initialize(config_manager, container, config, overrides)
            logger.debug("lazy initialized lifecycle executor")
        
        if not hasattr(container, 'llm_manager') or container.llm_manager is None:
            from optorch.llm.initializer import LlmPackageInitializer
            LlmPackageInitializer.initialize(config_manager, container, config, overrides)
            logger.debug("lazy initialized llm manager")
        
        required_attrs = ['intent_registry', 'tool_registry', 'transformer_registry', 'llm_registry', 'lifecycle_executor']
        missing = [attr for attr in required_attrs if not hasattr(container, attr) or getattr(container, attr) is None]
        
        if missing:
            logger.error(f"missing required dependencies after lazy init: {missing}")
            return None
        
        controller = NodeController.from_config(
            intent_registry=container.intent_registry,
            tool_registry=container.tool_registry,
            transformer_registry=container.transformer_registry,
            llm_registry=container.llm_registry,
            lifecycle_executor=container.lifecycle_executor,
            history=getattr(container, 'history', None),
            cache_manager=getattr(container, 'cache_manager', None),
            prompt_manager=getattr(container, 'prompt_manager', None),
        )
        
        container.node_controller = controller
        
        global_auto_discover = optorch_config.get("auto_discover", True)
        controller_config = optorch_config.get("controller", {})
        
        if controller_config is None or isinstance(controller_config, dict):
            package_auto_discover = (controller_config or {}).get("auto_discover", global_auto_discover)
        else:
            if "auto_discover" in controller_config.model_fields_set:
                package_auto_discover = controller_config.auto_discover
            elif controller_config.auto_discover is not None:
                package_auto_discover = controller_config.auto_discover
            else:
                package_auto_discover = global_auto_discover
        
        if package_auto_discover:
            ControllerPackageInitializer.discover(config_manager, container)
        else:
            logger.debug("auto_discover disabled (global or package level) - manual component registration required")
        
        logger.info("✅ NodeController initialized")
        
        return controller
    
    @staticmethod
    def discover(
        config_manager: ConfigManager,
        container: 'ApplicationContainer',
        force: bool = False
    ) -> None:
        """discover and register controller components (nodes + intents)
        
        args:
            config_manager: ConfigManager with nodes/intents configs
            container: ApplicationContainer with node_controller
            force: if True, ignores auto_discover flags and always discovers
        """
        from optorch.loader import AutoLoader
        from optorch.controller.config import ControllerConfig
        
        if not container or not container.node_controller:
            logger.warning("no node_controller - components not discovered")
            return
        
        controller = container.node_controller
        
        optorch_config = config_manager.get("optorch", {})
        global_auto_discover = optorch_config.get("auto_discover", True)
        
        controller_config_model = config_manager._get_typed_config("controller") if "controller" in config_manager._models else None
        controller_config: ControllerConfig | None = controller_config_model if isinstance(controller_config_model, ControllerConfig) else None
        
        if controller_config is None:
            controller_config = ControllerConfig()
        
        if "auto_discover" in controller_config.model_fields_set:
            package_auto_discover = controller_config.auto_discover
        elif controller_config.auto_discover is not None:
            package_auto_discover = controller_config.auto_discover
        else:
            package_auto_discover = global_auto_discover
        
        if not force and not package_auto_discover:
            logger.debug("controller auto_discover disabled (global or package level)")
            return
        
        paths = controller_config.discovery_paths
        
        base_module = optorch_config.get("application_module", "app")
        nodes_module = paths.nodes.module or f"{base_module}.nodes"
        intents_module = paths.intents.module or f"{base_module}.intents"
        tools_module = paths.tools.module or f"{base_module}.tools"
        
        if force or (package_auto_discover and paths.nodes.auto_discover):
            nodes_config = config_manager.get_hierarchical("nodes")
            if nodes_config:
                AutoLoader.register(controller.nodes, nodes_config, nodes_module, instantiate=paths.nodes.instantiate)
                logger.debug(f"discovered {len(nodes_config)} nodes from {nodes_module}")
        
        if force or (package_auto_discover and paths.intents.auto_discover):
            intents_config = config_manager.get_hierarchical("intents")
            if intents_config:
                AutoLoader.register(controller.intents, intents_config, intents_module, instantiate=paths.intents.instantiate)
                logger.debug(f"discovered {len(intents_config)} intents from {intents_module}")
        
        if force or (package_auto_discover and paths.tools.auto_discover):
            import importlib
            try:
                tools_mod = importlib.import_module(tools_module)
                tool_count = 0
                for name in getattr(tools_mod, '__all__', []):
                    tool_fn = getattr(tools_mod, name, None)
                    if tool_fn and hasattr(tool_fn, 'name'):
                        controller.tools.register(name, tool_fn)
                        tool_count += 1
                logger.debug(f"discovered {tool_count} tools from {tools_module}")
            except (ImportError, AttributeError) as e:
                logger.debug(f"tool discovery skipped: {e}")
    
    @staticmethod
    async def initialize_async(
        container: 'ApplicationContainer',
        entry_node: Optional[str] = None
    ) -> None:
        """async controller initialization - store node graph if storage available
        
        args:
            container: ApplicationContainer with node_controller
            entry_node: optional entry point for graph (reads from container if not provided)
        """
        if not container or not hasattr(container, 'node_controller') or not container.node_controller:
            logger.debug("no node_controller - async init skipped")
            return
        
        storage_manager = getattr(container, 'storage_manager', None)
        if storage_manager:
            node = entry_node or getattr(container, 'entry_node', 'product_discovery')
            await ControllerPackageInitializer.store_node_graph(container, node)
        else:
            logger.debug("no storage_manager - node graph won't be mapped")
    
    @staticmethod
    async def store_node_graph(
        container: 'ApplicationContainer',
        entry_node: str
    ) -> None:
        """map registered nodes to database for graph visualization
        
        uses live node registry from controller
        
        args:
            container: ApplicationContainer with storage_manager and node_controller
            entry_node: entry point node name for graph
        """
        from optorch.nodes.graph_mapper import NodeGraphMapper
        
        if not container:
            logger.debug("no container - node graph won't be mapped")
            return
        
        storage_manager = getattr(container, 'storage_manager', None)
        if not storage_manager:
            logger.debug("no storage_manager - node graph won't be mapped")
            return
        
        node_controller = getattr(container, 'node_controller', None)
        if not node_controller:
            logger.debug("no node_controller - node graph won't be mapped")
            return
        
        try:
            all_nodes = {}
            
            for node_name in node_controller._node_registry.list_keys():
                if node_controller._node_configs.has(node_name):
                    node_config = node_controller._node_configs.get(node_name)
                    all_nodes[node_name] = node_config.model_dump(by_alias=True, exclude_none=True)
            
            if not all_nodes:
                logger.debug("no nodes registered - skipping graph mapping")
                return
            
            mapper = NodeGraphMapper(storage_manager, all_nodes, entry_point=entry_node)
            count = await mapper.map_all_nodes()
            
            logger.info(f"✅ node graph mapped: {count} nodes")
        except Exception as e:
            logger.warning(f"node graph mapping failed: {e}", exc_info=True)
