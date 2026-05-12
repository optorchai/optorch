"""llm package initializer"""

from optorch.logging import get_logger
from typing import TYPE_CHECKING, Dict, Any, Optional

if TYPE_CHECKING:
    from optorch.config import ConfigManager
    from optorch.llm.manager import LLMManager
    from optorch.llm.prompt_manager import PromptManager
    from optorch.llm.config import PromptConfig
    from optorch.container import ApplicationContainer

logger = get_logger(__name__)


class LlmPackageInitializer:
    """self-contained llm system initialization"""
    
    @staticmethod
    def initialize(
        config_manager: 'ConfigManager',
        container: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        overrides: Optional[Dict[str, Any]] = None
    ) -> Optional['LLMManager']:
        """initialize llm system: pricing, embeddings, clients, manager, prompts
        
        args:
            config_manager: ConfigManager instance
            container: ApplicationContainer to attach to
            config: optional optorch config dict override
            overrides: optional dict overrides (provider-agnostic)
            
        returns:
            LLMManager instance or None
        """
        from optorch.llm.config import (
            LLMClientConfig, LLMConfig, LLMsConfig, 
            PromptConfig, SuggestionsConfig, 
            PromptRegistrationConfig
        )
        from optorch.llm.pricing.models import CostsConfig
        from optorch.llm.pricing import Pricing
        from optorch.llm.initialization import LLMInitializer
        from optorch.llm.manager import LLMManager
        from optorch.llm.prompt_manager import PromptManager
        from optorch.llm.fragments.base import Fragment
        from optorch.llm.client_factory import ClientFactory
        from optorch.initializer_utils import extract_optorch_config
        
        if not container:
            logger.warning("no container provided - llm system not initialized")
            return None
        
        if hasattr(container, 'llm_manager') and container.llm_manager:
            logger.debug("llm system already initialized - skipping")
            return container.llm_manager
        
        optorch_config = extract_optorch_config(config_manager, config)
        
        config_manager.register_config("llm_clients", LLMClientConfig)
        config_manager.register_config("llm", LLMConfig)
        config_manager.register_config("llms", LLMsConfig)
        config_manager.register_config("prompts", PromptConfig)
        config_manager.register_config("suggestions", SuggestionsConfig)
        config_manager.register_config("prompt_registration", PromptRegistrationConfig)
        config_manager.register_config("costs", CostsConfig)
        logger.debug("✅ LLM config models registered")
        
        if overrides:
            for key in ["llm_clients", "llm", "llms", "prompts", "suggestions", "prompt_registration", "costs"]:
                merged = config_manager.merge_overrides(key, overrides, isolate=True)
                optorch_config[key] = merged
        
        costs_config = optorch_config.get("costs")
        if costs_config:
            Pricing.initialize(CostsConfig(**costs_config))
            logger.info(f"✅ Initialized LLM price tracking with {len(costs_config.get('pricing', {}))} models")
        else:
            Pricing.initialize()
            logger.info("✅ Initialized LLM price tracking with defaults")
        
        if not hasattr(container, 'llm_registry') or not container.llm_registry:
            logger.warning("No LLM registry in container - skipping client registration")
            manager = LLMManager()
            container.llm_manager = manager
            return manager
        
        client_dict = optorch_config.get("llm_clients", {})
        client_config = LLMClientConfig(**client_dict) if client_dict else LLMClientConfig()
        factory = ClientFactory(client_config.providers, client_config.module)
        
        llms_config = optorch_config.get("llms") or {}
        llm_initializer = LLMInitializer(factory, container.llm_registry, llms_config, config_manager)
        llm_initializer.initialize()
        logger.debug("✅ LLM clients registered to registry")
        
        manager = LLMManager()
        llm_dict = optorch_config.get("llm", {})
        if llm_dict:
            llm_config = LLMConfig(**llm_dict)
            manager.set_config(llm_config.model_dump())
        manager.set_llm_registry(container.llm_registry)
        container.llm_manager = manager
        logger.info("✅ LLMManager initialized")
        
        prompt_manager = PromptManager()
        prompts_dict = optorch_config.get("prompts", {})
        prompts_config = PromptConfig(**prompts_dict) if prompts_dict else PromptConfig()
        
        for name, content in prompts_config.fragments.items():
            prompt_manager.fragment.register(Fragment(name, content))
        if prompts_config.fragments:
            logger.info(f"Registered {len(prompts_config.fragments)} prompt fragments")
        
        LlmPackageInitializer._register_prompt_providers(prompt_manager, prompts_config, config_manager)
        
        container.prompt_manager = prompt_manager
        logger.info("✅ Prompt system initialized")
        
        llm_config_dict = optorch_config.get("llm", {})
        optorch_auto_discover = optorch_config.get("auto_discover", True)
        
        if llm_config_dict is None or isinstance(llm_config_dict, dict):
            package_auto_discover = (llm_config_dict or {}).get("auto_discover", optorch_auto_discover)
        else:
            if "auto_discover" in llm_config_dict.model_fields_set:
                package_auto_discover = llm_config_dict.auto_discover
            else:
                package_auto_discover = optorch_auto_discover
        
        if package_auto_discover:
            LlmPackageInitializer.discover(config_manager, container)
        else:
            logger.debug("llm auto_discover disabled (global or package level) - manual transformer registration required")
        
        return manager
    
    @staticmethod
    def _register_prompt_providers(prompt_manager: 'PromptManager', config: 'PromptConfig', config_manager: 'ConfigManager') -> None:
        """Register prompt providers based on config (supports runtime overrides)"""
        from optorch.llm.prompts import (
            LocalPromptProvider, 
            DictPromptProvider, 
            CallablePromptProvider
        )
        from optorch.llm.prompts.redis_provider import RedisPromptProvider
        from optorch.llm.prompts.qdrant_provider import QdrantPromptProvider
        from optorch.session.storage import RedisConfig
        from typing import Callable
        
        # priority 10: inline dict (highest - library mode override)
        if config.inline_prompts:
            provider = DictPromptProvider(config.inline_prompts)
            prompt_manager.provider.register(provider, priority=10)
            logger.info(f" - Registered DictPromptProvider with {len(config.inline_prompts)} prompts")
        
        # priority 20: callable loader (dynamic)
        if config.loader_callable and callable(config.loader_callable):
            loader: Callable[[str], str | None] = config.loader_callable  # type: ignore[assignment]
            provider = CallablePromptProvider(loader)
            prompt_manager.provider.register(provider, priority=20)
            logger.info(" - Registered CallablePromptProvider")
        
        # priority 30: redis cache (hot-reload) - only if configured
        redis_config = config.redis
        if not redis_config:
            session_config = config_manager.get("session", {})
            if isinstance(session_config, dict):
                storage = session_config.get("storage", {})
                if isinstance(storage, dict):
                    redis_dict = storage.get("redis")
                    if redis_dict:
                        redis_config = RedisConfig(**redis_dict) if isinstance(redis_dict, dict) else redis_dict
        
        if redis_config:
            redis_url = redis_config.url
            redis_provider = RedisPromptProvider(redis_url)
            prompt_manager.provider.register(redis_provider, priority=30)
            logger.info(f" - Registered RedisPromptProvider (url: {redis_url})")
        
        # priority 40: qdrant semantic search - only if configured
        qdrant_config = config.qdrant
        if qdrant_config:
            qdrant_url = qdrant_config.url
            qdrant_collection = qdrant_config.collection if qdrant_config.collection else "prompts"
            qdrant_provider = QdrantPromptProvider(qdrant_url, qdrant_collection)
            prompt_manager.provider.register(qdrant_provider, priority=40)
            logger.info(f" - Registered QdrantPromptProvider (url: {qdrant_url}, collection: {qdrant_collection})")
        
        # priority 50-60: custom providers (auto-discovered)
        if config.auto_discover:
            LlmPackageInitializer._discover_custom_providers(prompt_manager, config)
        
        # priority 100: file-based (default fallback)
        provider = LocalPromptProvider(config.directory)
        prompt_manager.provider.register(provider, priority=100)
        logger.info(f" - Registered LocalPromptProvider (directory: {config.directory})")
    
    @staticmethod
    def _discover_custom_providers(prompt_manager: 'PromptManager', config: 'PromptConfig') -> None:
        """Auto-discover and register custom PromptProvider classes
        
        Tries module patterns from config.providers_modules (defaults to common patterns)
        """
        from optorch.loader import AutoLoader
        from optorch.llm.prompts import PromptProvider
        import importlib
        import inspect
        
        modules_to_try = config.providers_modules
        
        for module_path in modules_to_try:
            try:
                module = importlib.import_module(module_path)
                discovered = 0
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # skip abstract base and built-ins
                    if obj is PromptProvider or not issubclass(obj, PromptProvider):
                        continue
                    if obj.__module__ != module_path:
                        continue
                    
                    try:
                        provider_instance = obj()
                        prompt_manager.provider.register(provider_instance, priority=30)
                        logger.info(f" - Registered custom provider: {name}")
                        discovered += 1
                    except Exception as e:
                        logger.warning(f"Failed to instantiate {name}: {e}")
                
                if discovered > 0:
                    logger.info(f"✅ Discovered {discovered} custom prompt providers from {module_path}")
                    return 
                else:
                    logger.debug(f"No custom providers found in {module_path}")
                    
            except ImportError:
                logger.debug(f"Module '{module_path}' not found - trying next pattern")
                continue
            except Exception as e:
                logger.warning(f"Custom provider discovery failed for {module_path}: {e}")
                continue
        
        logger.debug("No custom prompt providers discovered from common patterns")


    
    @staticmethod
    def discover(
        config_manager: 'ConfigManager',
        container: Optional['ApplicationContainer'] = None,
        force: bool = False
    ) -> None:
        """discover and register transformers from config
        
        args:
            config_manager: ConfigManager with transformers config
            container: ApplicationContainer with transformer_registry
            force: if True, ignores auto_discover flags and always discovers
        """
        from optorch.loader import AutoLoader
        from optorch.llm.config import LLMConfig
        
        if not container:
            logger.warning("No container - transformers not discovered")
            return
        
        # transformers can register to controller.transformers OR container.transformer_registry
        if hasattr(container, 'node_controller') and container.node_controller:
            transformer_registry = container.node_controller._transformer_registry
        elif hasattr(container, 'transformer_registry') and container.transformer_registry:
            transformer_registry = container.transformer_registry
        else:
            logger.warning("No transformer registry - transformers not discovered")
            return
        
        optorch_config = config_manager.get("optorch", {})
        global_auto_discover = optorch_config.get("auto_discover", True)
        
        llm_config_model = config_manager._get_typed_config("llm") if "llm" in config_manager._models else None
        llm_config: LLMConfig | None = llm_config_model if isinstance(llm_config_model, LLMConfig) else None
        
        if llm_config is None:
            package_auto_discover = global_auto_discover
        else:
            if "auto_discover" in llm_config.model_fields_set:
                package_auto_discover = llm_config.auto_discover
            else:
                package_auto_discover = global_auto_discover
        
        if not force and not package_auto_discover:
            logger.debug("LLM auto_discover disabled (global or package level)")
            return
        
        if llm_config and llm_config.transformers and (force or (package_auto_discover and llm_config.transformers.auto_discover)):
            transformers_config = config_manager.get("transformers")
            if transformers_config:
                ok, fail = AutoLoader.register(
                    transformer_registry,
                    transformers_config,
                    llm_config.transformers.module,
                    instantiate=llm_config.transformers.instantiate
                )
                logger.info(f"✅ Discovered {ok} transformers from {llm_config.transformers.module} ({fail} failed)")
            else:
                logger.warning("No transformers config found - skipping transformer discovery")