from optorch.logging import get_logger
from typing import Any, Callable
from .prompt_provider import PromptProvider

logger = get_logger(__name__)


class CallablePromptProvider(PromptProvider):
    """Loads prompts via callable for dynamic sources"""
    
    def __init__(self, loader: Callable[[str], str | None]) -> None:
        self._loader = loader
    
    async def load(self, prompt_name: str, fragments: dict[str, Any]) -> str | None:
        """Load prompt via callable and apply fragment replacements"""
        try:
            template = self._loader(prompt_name)
            if not template:
                logger.debug(f"Callable provider: returned None for '{prompt_name}'")
                return None
            
            # Fragment injection
            for key, value in fragments.items():
                placeholder = f"{{{key}}}"
                template = template.replace(placeholder, value if value else "")
            
            logger.info(f"Loaded '{prompt_name}' from callable provider")
            return template
        except Exception as e:
            logger.debug(f"Callable provider failed for '{prompt_name}': {str(e)}")
            return None
    
    @property
    def name(self) -> str:
        return "Callable"
