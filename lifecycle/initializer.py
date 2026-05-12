"""lifecycle package initializer"""

from optorch.logging import get_logger
from typing import TYPE_CHECKING, Dict, Any, Optional

if TYPE_CHECKING:
    from optorch.container import ApplicationContainer

from optorch.config import ConfigManager

logger = get_logger(__name__)


class LifecyclePackageInitializer:
    """self-contained lifecycle initialization"""
    
    @staticmethod
    def initialize(
        config_manager: ConfigManager,
        container: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """initialize lifecycle executor and ensure registries exist
        
        args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
            
        returns:
            LifecycleExecutor instance or None
        """
        from optorch.lifecycle.lifecycle_executor import LifecycleExecutor
        from optorch.lifecycle.config import LifecycleConfig
        from optorch.initializer_utils import extract_optorch_config
        
        if not container:
            logger.warning("No container provided - lifecycle executor not initialized")
            return None
        
        if hasattr(container, 'lifecycle_executor') and container.lifecycle_executor:
            logger.debug("lifecycle executor already initialized - skipping")
            return container.lifecycle_executor
        
        if not hasattr(container, 'intent_registry') or container.intent_registry is None:
            LifecyclePackageInitializer._initialize_registries(container)
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        config_manager.register_config("lifecycle", LifecycleConfig)
        logger.debug("✅ lifecycle config model registered")
        
        if overrides:
            lifecycle_dict = config_manager.merge_overrides("lifecycle", overrides, isolate=True)
            optorch_config["lifecycle"] = lifecycle_dict
        
        executor = LifecycleExecutor.from_config(optorch_config, container.intent_registry)
        container.lifecycle_executor = executor
        
        logger.info("✅ LifecycleExecutor initialized")
        
        return executor
    
    @staticmethod
    def _initialize_registries(container: Any) -> None:
        """lazy create core registries if not present"""
        from optorch.intents.intent_registry import IntentRegistry
        from optorch.tools.tool_registry import ToolRegistry
        from optorch.transformers.transformer_registry import TransformerRegistry
        from optorch.llm.llm_registry import LLMRegistry
        from optorch.intents.llm_context_lifecycle import CreateLLMContext
        
        if not hasattr(container, 'intent_registry') or container.intent_registry is None:
            container.intent_registry = IntentRegistry()
            container.intent_registry.register("create_llm_context", CreateLLMContext())
        
        if not hasattr(container, 'tool_registry') or container.tool_registry is None:
            container.tool_registry = ToolRegistry()
            
            from optorch.tools.tools_config import ToolsConfig
            container.config_manager.register_config("tools", ToolsConfig)
        
        if not hasattr(container, 'transformer_registry') or container.transformer_registry is None:
            container.transformer_registry = TransformerRegistry()
        
        if not hasattr(container, 'llm_registry') or container.llm_registry is None:
            container.llm_registry = LLMRegistry()