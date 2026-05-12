from optorch.logging import get_logger
from typing import Any
from .prompt_provider import PromptProvider

logger = get_logger(__name__)


class DictPromptProvider(PromptProvider):
    """Loads prompts from inline dict for library mode"""
    
    def __init__(self, prompts: dict[str, str]) -> None:
        self._prompts = prompts
    
    async def load(self, prompt_name: str, fragments: dict[str, Any]) -> str | None:
        """Load prompt from dict and apply fragment replacements"""
        template = self._prompts.get(prompt_name)
        if not template:
            logger.debug(f"Dict provider: prompt '{prompt_name}' not found")
            return None
        
        for key, value in fragments.items():
            placeholder = f"{{{key}}}"
            template = template.replace(placeholder, value if value else "")
        
        logger.info(f"Loaded '{prompt_name}' from dict provider")
        return template
    
    @property
    def name(self) -> str:
        return "Dict"
