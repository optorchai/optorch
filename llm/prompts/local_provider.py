import os
from optorch.logging import get_logger
from typing import Any
from .prompt_provider import PromptProvider

logger = get_logger(__name__)

class LocalPromptProvider(PromptProvider):
    
    def __init__(self, prompts_dir: str = "prompts") -> None:
        self.prompts_dir = prompts_dir
    
    async def load(self, prompt_name: str, fragments: dict[str, Any]) -> str | None:
        """Load prompt from local filesystem and apply fragment replacements"""
        try:
            prompt_file = os.path.join(self.prompts_dir, f"{prompt_name}.md")
            with open(prompt_file, 'r') as f:
                content = f.read()
            
            # Replace fragment placeholders
            for key, value in fragments.items():
                placeholder = f"{{{key}}}"
                content = content.replace(placeholder, value if value else "")
            
            logger.info(f"Loaded '{prompt_name}' from local provider")
            return content
        except Exception as e:
            logger.debug(f"Local load failed for '{prompt_name}': {str(e)}")
            return None
    
    @property
    def name(self) -> str:
        return "Local"
