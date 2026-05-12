"""Generic LLM system initialization"""
from optorch.logging import get_logger
from typing import Dict, Any, List, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.llm.llm_registry import LLMRegistry
    from optorch.config.manager import ConfigManager

logger = get_logger(__name__)

CLIENT_PARAMS = {'api_key', 'model', 'temperature', 'tpm_limit'}
INSTANCE_ATTRS = {'completion_type', 'streaming'}


class LLMClientFactoryProtocol(Protocol):
    """protocol for LLM client factories"""
    providers: Dict[str, str]
    module: str
    
    def create(self, provider: str, config: Dict[str, Any]) -> Any: ...
    def create_pool_clients(self, provider: str, config: Dict[str, Any], api_keys: List[str]) -> List[Any]: ...


class LLMInitializer:
    """
    Generic LLM system initializer.
    Reads config and registers clients/pools using a factory.
    """
    
    def __init__(
        self,
        client_factory: LLMClientFactoryProtocol,
        llm_registry: 'LLMRegistry',
        llms_config: Dict[str, Any],
        config_manager: 'ConfigManager'
    ) -> None:
        """
        Args:
            client_factory: Factory with create() and create_pool_clients() methods
            llm_registry: LLMRegistry instance from LLMManager
            llms_config: LLM configurations from optorch.llms
            config_manager: ConfigManager for secret access
        """
        self.client_factory: LLMClientFactoryProtocol = client_factory
        self.llm_registry: 'LLMRegistry' = llm_registry
        self.llms_config: Dict[str, Any] = llms_config or {}
        self.config_manager: 'ConfigManager' = config_manager
    
    def initialize(self) -> None:
        """
        Initialize LLM clients and pools from config provided in constructor.
        
        Processes optorch.llms for individual clients and optorch.llm_pools for pools.
        """
        logger.debug(f"Initializing LLMs from config: {list(self.llms_config.keys()) if self.llms_config else 'NONE'}")
        
        if not self.llms_config:
            logger.warning("No LLMs configured in optorch.llms")
        else:
            for name, llm_config in self.llms_config.items():
                logger.debug(f"Processing LLM '{name}': {llm_config}")
                provider = llm_config.get("provider")
                if not provider:
                    logger.warning(f"No provider specified for '{name}', skipping")
                    continue
                
                llm_type = llm_config.get("type", "client")
                
                if llm_type == "pool":
                    self._register_pool(name, provider, llm_config)
                else:
                    self._register_client(name, provider, llm_config)
        
        pools_config = self.config_manager.get("optorch.llm_pools")
        if pools_config:
            logger.debug(f"Initializing LLM pools: {list(pools_config.keys())}")
            for pool_name, pool_config in pools_config.items():
                self._register_pool_from_clients(pool_name, pool_config)
    
    def _register_pool_from_clients(self, name: str, config: Dict[str, Any]) -> None:
        """Register a pool from existing client references"""
        clients = config.get("clients", [])
        strategy = config.get("strategy", "round_robin")
        
        if not clients:
            logger.warning(f"Pool '{name}' has no clients configured, skipping")
            return
        
        pool_clients = []
        for client_name in clients:
            client = self.llm_registry.get(client_name)
            if client:
                pool_clients.append(client)
            else:
                logger.warning(f"Client '{client_name}' not found for pool '{name}', skipping")
        
        if len(pool_clients) < 2:
            logger.warning(f"Pool '{name}' needs at least 2 valid clients, found {len(pool_clients)}, skipping")
            return
        
        self.llm_registry.register_pool(name, pool_clients, strategy=strategy)
        logger.debug(f"Registered pool '{name}': {len(pool_clients)} clients ({strategy})")
    
    def _register_pool(self, name: str, provider: str, config: Dict[str, Any]) -> None:
        """Register a pool of LLM clients"""
        strategy = config.get("strategy", "round_robin")
        key_prefix = config.get("key_prefix", f"{provider.upper()}_API_KEY")
        
        api_keys = self._collect_api_keys(key_prefix)
        
        if len(api_keys) < 2:
            logger.warning(
                f"Pool '{name}' needs at least 2 API keys, found {len(api_keys)}, skipping"
            )
            return
        
        pool_clients = self.client_factory.create_pool_clients(provider, config, api_keys)
        
        if not pool_clients:
            logger.warning(f"Failed to create pool clients for '{name}', skipping")
            return
        
        self.llm_registry.register_pool(name, pool_clients, strategy=strategy)
        logger.debug(
            f"Registered pool '{name}': {len(pool_clients)} x "
            f"{provider}/{config.get('model')} ({strategy})"
        )
    
    def _register_client(self, name: str, provider: str, config: Dict[str, Any]) -> None:
        """Register a single LLM client"""
        if "api_key" not in config:
            api_key = self._get_api_key(provider, config)
            if api_key:
                config = {**config, "api_key": api_key}
        
        client_params = {k: v for k, v in config.items() if k in CLIENT_PARAMS}
        client = self.client_factory.create(provider, client_params)
        
        if not client:
            logger.warning(f"Failed to create client for '{name}', skipping")
            return
        
        for attr in INSTANCE_ATTRS:
            if attr in config:
                setattr(client, attr, config[attr])
        
        self.llm_registry.register(name, client)
        logger.debug(f"Registered client '{name}': {provider}/{config.get('model')}")
    
    def _get_api_key(self, provider: str, config: Dict[str, Any]) -> str | None:
        """Get API key via ConfigManager using key_prefix or provider default"""
        key_prefix = config.get("key_prefix", f"{provider.upper()}_API_KEY")
        return self.config_manager.get_secret(key_prefix)
    
    def _collect_api_keys(self, key_prefix: str) -> List[str]:
        """Collect API keys with numeric suffixes via ConfigManager"""
        api_keys = []
        key_index = 1
        
        while True:
            key_var = key_prefix if key_index == 1 else f"{key_prefix}_{key_index}"
            key = self.config_manager.get_secret(key_var)
            if not key:
                break
            api_keys.append(key)
            key_index += 1
        
        return api_keys
