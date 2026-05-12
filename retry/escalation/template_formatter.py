"""Escalation template formatter with fragment injection"""
import os
from optorch.logging import get_logger
from pathlib import Path
from typing import Optional, Any
from optorch.utils import sanitize_path

logger = get_logger(__name__)


class EscalationFormatter:
    """Formats escalation messages using templates and fragments"""
    
    def __init__(self, prompt_manager: Optional[Any] = None, templates_dir: Optional[str] = None):
        """
        Initialize formatter.
        
        Args:
            prompt_manager: PromptManager instance for fragment injection
            templates_dir: Absolute path to templates directory (defaults to app/prompts/escalations)
        """
        self.prompt_manager = prompt_manager
        
        if not templates_dir:
            # Default to app/prompts/escalations relative to project root
            # overridden by nodes that pass explicit path
            project_root = Path(__file__).parent.parent.parent
            self.templates_dir = sanitize_path(str(project_root),"app","prompts","escalations")
        else:
            self.templates_dir = templates_dir
    
    def format(self, template_name: str, **context) -> str:
        """
        Load escalation template, inject fragments and context.
        
        Args:
            template_name: Name of template file (without .md extension)
            **context: Variables to inject into template (error, context, etc.)
        
        Returns:
            Formatted message with fragments and context injected
        """
        try:
            template_path = sanitize_path(self.templates_dir, f"{template_name}.md")
            
            with open(template_path, 'r') as f:
                template = f.read()
            
            fragments = {}
            if self.prompt_manager:
                try:
                    all_fragments = self.prompt_manager._fragment_registry.load_all()
                    fragments.update(all_fragments)
                except Exception as e:
                    logger.warning(f"Failed to load fragments: {e}")
            
            fragments.update(context)
            
            result = template
            for key, value in fragments.items():
                placeholder = f"{{{key}}}"
                result = result.replace(placeholder, str(value) if value else "")
            
            return result
            
        except FileNotFoundError:
            logger.error(f"Escalation template not found: {template_name}")
            return f"I encountered an error: {context.get('error', 'Unknown error')}. Could you help?"
        except Exception as e:
            logger.error(f"Failed to format escalation template {template_name}: {e}")
            return f"I encountered an error: {context.get('error', 'Unknown error')}. Could you help?"
