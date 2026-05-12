"""LLM client factory - loads client classes from YAML config via AutoLoader"""
from optorch.logging import get_logger
from typing import Dict, List, Any, Optional

from optorch.loader import AutoLoader

logger = get_logger(__name__)


class ClientFactory:
    """Runtime factory that loads LLM client classes from config
    
    Pattern: optorch.yaml defines provider -> class mappings
    AutoLoader discovers classes at runtime
    No hardcoded imports needed
    
    Config:
        llm_clients:
          providers:
            openai: OpenAIClient
            groq: GroqClient
            ollama: OllamaClient
          module: app.llm.clients
    
    Usage:
        factory = ClientFactory(providers, module)
        client = factory.create("openai", {"api_key": "..."})
    """
    
    def __init__(self, providers: Dict[str, str], module: str = "app.llm.clients"):
        """Initialize factory with provider -> class mappings
        
        Args:
            providers: Dict mapping provider names to class names
            module: Base module path for AutoLoader discovery
        """
        self.providers = providers
        self.module = module
    
    def create(self, provider: str, config: Dict[str, Any]) -> Optional[Any]:
        """Create single client instance for provider
        
        Args:
            provider: Provider name (openai, groq, etc)
            config: Client configuration dict
        
        Returns:
            Client instance or None if provider unknown/failed
        """
        class_name = self.providers.get(provider)
        if not class_name:
            logger.error(f"Unknown provider: {provider}")
            return None
        
        try:
            client_class = AutoLoader.load_class(class_name, provider, self.module)
            return client_class(**config)
        except Exception as e:
            logger.error(f"Failed to create {provider} client: {e}")
            return None
    
    def create_pool_clients(
        self, 
        provider: str, 
        config: Dict[str, Any], 
        api_keys: List[str]
    ) -> List[Any]:
        """Create pool of clients with different API keys
        
        Args:
            provider: Provider name
            config: Base client config
            api_keys: List of API keys for pool
        
        Returns:
            List of client instances (empty if provider unknown/failed)
        """
        class_name = self.providers.get(provider)
        if not class_name:
            return []
        
        try:
            client_class = AutoLoader.load_class(class_name, provider, self.module)
            return [client_class(**{**config, "api_key": key}) for key in api_keys]  # Unpack as kwargs
        except Exception as e:
            logger.error(f"Failed to create {provider} pool: {e}")
            return []
