"""Prompt management with fragments"""
from optorch.logging import get_logger
from typing import Any, List, Optional
from optorch.llm.prompts import PromptProvider
from optorch.llm.fragments import FragmentRegistry, Fragment

logger = get_logger(__name__)


class FragmentManager:
    """Manages fragment registration"""
    def __init__(self, registry: FragmentRegistry):
        self._registry = registry
    
    def register(self, fragment: Fragment):
        """Register a prompt fragment"""
        self._registry.register(fragment)
    
    def get(self, name: str) -> Fragment | None:
        """Get a registered fragment by name"""
        return self._registry._fragments.get(name)


class ProviderManager:
    """Manages provider registration"""
    def __init__(self, providers: List):
        self._providers = providers
    
    def register(self, provider_instance: PromptProvider, priority: int = 99):
        """Register a prompt provider with priority (lower = tried first)"""
        self._providers.append((priority, provider_instance))
        self._providers.sort(key=lambda x: x[0])


class PromptManager:
    """
    Manages prompt loading and runnable creation.
    Handles fragments, providers, and LangChain chain building.
    """
    
    def __init__(self):
        self._fragment_registry = FragmentRegistry()
        self._providers: List[tuple[int, PromptProvider]] = []
        self.fragment = FragmentManager(self._fragment_registry)
        self.provider = ProviderManager(self._providers)
    
    async def load_template(self, prompt_name: str) -> Optional[str]:
        """Load prompt template from registered providers and inject fragments."""
        fragments = self._fragment_registry.load_all()
        
        for priority, provider in self._providers:
            template = await provider.load(prompt_name, fragments)
            if template:
                logger.debug(f"Loaded prompt '{prompt_name}' from {provider.name}")
                return template
        
        logger.warning(f"No provider could load prompt '{prompt_name}'")
        return None
    
    async def load_prompt(self, prompt_name: str) -> Optional[str]:
        """
        Load prompt template as string.
        Convenience method that calls load_template.
        
        Args:
            prompt_name: Name of prompt to load
        
        Returns:
            Prompt template string with fragments injected
        
        Usage:
            prompt = await prompt_manager.load_prompt("tariff_prompt")
        """
        return await self.load_template(prompt_name)
