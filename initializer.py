"""Core optorch initialization - wires up all components from config"""
from optorch.logging import get_logger
import importlib
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from optorch.container import ApplicationContainer
    from optorch.config import ConfigManager

logger = get_logger(__name__)


def initialize(
    container: Optional['ApplicationContainer'] = None,
    config: Optional['ConfigManager'] = None,
    config_override: Optional[Dict[str, Any]] = None
) -> 'ApplicationContainer':
    """Initialize core optorch components - factory mode or populate existing container
    
    Args:
        container: Optional pre-created container. If None, creates new one.
        config: Optional config manager. If None, creates with Pydantic defaults.
        config_override: Optional runtime config dict to merge (e.g., {"prompts": {"inline_prompts": {...}}})
    
    Returns:
        Fully initialized ApplicationContainer
    
    Usage:
        # Zero-config mode (library)
        container = initialize_optorch()
        
        # Custom config (library)
        config = ConfigManager("/path/to/config")
        container = initialize_optorch(config=config)
        
        # Existing container (app integration)
        container = ApplicationContainer(config.optorch.model_dump())
        initialize_optorch(container, config)
    
    Sets up:
    - Error handling policies
    - Session manager
    - Core registries (intent, tool, transformer, LLM)
    - Lifecycle executor
    - Node controller
    - LLM system (cache, history, manager)
    - Filters
    - Transport registry (UI communication)
    - Extensions (budget, interact) via auto-discovery
    
    Does NOT initialize:
    - MCP - use McpPackageInitializer.initialize() + .connect()
    - App-specific registrations - handled by app layer
    """
    from optorch.container import ApplicationContainer
    from optorch.config import ConfigManager
    
    if config is None:
        if container is not None and container.config_manager is not None:
            config = container.config_manager
        else:
            config = ConfigManager()
    
    if container is None:
        container = ApplicationContainer(config_manager=config)
    elif container.config_manager is None:
        container.config_manager = config
    
    _configure_error_handling(config_manager=config)
    _initialize_packages(config_manager=config, container=container, config_override=config_override)
    
    return container

async def initialize_async(
    container: 'ApplicationContainer',
    entry_node: Optional[str] = None
) -> None:
    """Async optorch initialization - migrations, connections, etc
    
    Calls initialize_async() on all packages that have it.
    
    CRITICAL ORDER:
    1. Config DB migrations (if DatabaseProvider used)
    2. Core storage migrations
    3. Identity migrations (if dedicated storage)
    4. Other packages
    
    Args:
        container: Initialized ApplicationContainer from initialize()
        entry_node: Optional entry point for node graph storage
    """
    # STEP 1: Initialize config DB if using DatabaseProvider
    if hasattr(container, 'config_manager') and container.config_manager:
        from optorch.config.providers.database import DatabaseConfigProvider
        provider = container.config_manager.provider
        if isinstance(provider, DatabaseConfigProvider):
            await provider.initialize_async()
            logger.debug("✅ config provider async init complete")
    
    packages_with_async = [
        ("storage", True, {"entry_node": entry_node}),
        ("controller", True, {"entry_node": entry_node}),
        ("identity", False, {}),
        ("mcp", False, {}),
        ("transport", False, {}),
    ]
    
    for pkg_name, required, kwargs in packages_with_async:
        try:
            module = importlib.import_module(f"optorch.{pkg_name}.initializer")
            initializer_class = getattr(module, f"{pkg_name.capitalize()}PackageInitializer")
            
            if hasattr(initializer_class, 'initialize_async'):
                await initializer_class.initialize_async(container, **kwargs)
                log_msg = f"✅ {pkg_name} async init complete" if required else f"✅ {pkg_name} async init complete"
                logger.debug(log_msg)
        except ImportError:
            if required:
                raise
            logger.debug(f"{pkg_name} extension not installed - skipping async init")
    
    # async init for extensions
    import pkgutil
    try:
        import extensions
        
        for finder, ext_name, is_pkg in pkgutil.iter_modules(extensions.__path__):
            if not is_pkg:
                continue
            
            try:
                module = importlib.import_module(f"extensions.{ext_name}.initializer")
                initializer_class = getattr(module, f"{ext_name.capitalize()}PackageInitializer")
                
                if hasattr(initializer_class, 'initialize_async'):
                    await initializer_class.initialize_async(container)
                    logger.info(f"✅ {ext_name} async init complete")
            except (ImportError, AttributeError) as e:
                logger.debug(f"{ext_name} extension has no async init - skipping: {e}")
            except Exception as e:
                logger.warning(f"{ext_name} async init failed: {e}", exc_info=True)
    except ImportError:
        logger.debug("No extensions package found")


def discover(
    config_manager: 'ConfigManager',
    container: 'ApplicationContainer',
    force: bool = True
) -> None:
    """discover and register all components from configs across all packages
    
    manual discovery call - ignores auto_discover flags by default.
    use after initialize() when optorch.auto_discover=False but you want explicit discovery.
    
    calls discover() on each package that has components:
    - controller: nodes, intents
    - llm: transformers
    - mcp: tools (app-defined, MCP server tools auto-discovered on connect)
    - budget: custom scopes, enforcement
    - filters: custom filters
    - storage: custom queries
    
    args:
        config_manager: ConfigManager with all component configs
        container: Initialized ApplicationContainer
        force: if True (default), ignores auto_discover flags and always discovers
    """
    packages_with_discovery = [
        ("controller", True),
        ("llm", False),
        ("mcp", False),
        ("interact", False),
        ("budget", False),
        ("filters", False),
        ("storage", False),
    ]
    
    for pkg_name, required in packages_with_discovery:
        try:
            module = importlib.import_module(f"optorch.{pkg_name}.initializer")
            initializer_class = getattr(module, f"{pkg_name.capitalize()}PackageInitializer")
            
            if hasattr(initializer_class, 'discover'):
                initializer_class.discover(config_manager, container, force=force)
                logger.debug(f"✅ {pkg_name} components discovered")
        except ImportError:
            if required:
                raise
            logger.debug(f"{pkg_name} package not installed - skipping discovery")
        except Exception as e:
            if required:
                raise
            logger.warning(f"{pkg_name} async init failed: {e}")


def _configure_error_handling(config_manager: 'ConfigManager') -> None:
    from optorch.errors import ErrorHandler
    from optorch.errors.config import ErrorsConfig
    
    config_manager.register_config("optorch.errors", ErrorsConfig)
    
    errors_config = config_manager.get("optorch.errors")
    if not errors_config:
        errors_config = ErrorsConfig()
    
    if isinstance(errors_config, dict):
        errors_config = ErrorsConfig(**errors_config)
    
    ErrorHandler.configure(policy=errors_config.policy.model_dump())
    logger.info("Error handling policy configured")


def _initialize_packages(
    config_manager: 'ConfigManager', 
    container: 'ApplicationContainer',
    config_override: Optional[Dict[str, Any]] = None
) -> None:
    """initialize all optorch packages in dependency order
    
    required packages (order matters - dependencies first):
    - logging: configure root logger FIRST (all packages use loggers)
    - cache, session: no dependencies
    - lifecycle: creates empty registries
    - llm: populates llm_registry
    - controller: uses llm_registry, lifecycle_executor
    - history: uses session, cache
    - filters: standalone registry
    
    optional packages (auto-discovered, order doesn't matter):
    - storage, budget, interact (gracefully skip if not installed)
    """
    packages = [
        ("logging", True),
        ("events", True),
        ("cache", True),
        ("session", True),
        ("lifecycle", True),
        ("llm", True),
        ("controller", True),
        ("history", True),
        ("filters", True),
        ("transport", True),
        ("mcp", False),
        ("storage", False),
        ("identity", False),
    ]
    
    for pkg_name, required in packages:
        try:
            module = importlib.import_module(f"optorch.{pkg_name}.initializer")
            initializer_class = getattr(module, f"{pkg_name.capitalize()}PackageInitializer")
            initializer_class.initialize(config_manager=config_manager, container=container, config=config_override)
            log_msg = f"✅ {pkg_name} package initialized" if required else f"✅ {pkg_name} extension initialized"
            logger.debug(log_msg) if required else logger.info(log_msg)
        except ImportError:
            if required:
                raise
            logger.debug(f"{pkg_name} extension not installed - skipping")
        except Exception as e:
            if required:
                raise
            logger.warning(f"{pkg_name} extension initialization failed: {e}")
    
    import pkgutil
    
    try:
        import extensions
        
        for finder, ext_name, is_pkg in pkgutil.iter_modules(extensions.__path__):
            if not is_pkg:
                continue
            
            try:
                module = importlib.import_module(f"extensions.{ext_name}.initializer")
                initializer_class = getattr(module, f"{ext_name.title().replace('_', '')}PackageInitializer")
                initializer_class.initialize(config_manager=config_manager, container=container, config=config_override)
                logger.info(f"✅ {ext_name} extension initialized")
            except (ImportError, AttributeError) as e:
                logger.debug(f"Extension {ext_name} has no initializer: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize extension {ext_name}: {e}")
    except ImportError:
        logger.debug("No extensions package installed")
