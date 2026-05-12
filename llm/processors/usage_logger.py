"""Usage logger processor - FINALIZE - logs token usage"""

from optorch.logging import get_logger

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.events.decorators import emits
from optorch.constants import EventTypes

logger = get_logger(__name__)

class UsageLogger(BaseLLMProcessor):
    """Log token usage and emit usage events"""
    
    def __init__(self):
        super().__init__()
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.FINALIZE
    
    @emits(EventTypes.LLM)
    async def process(self, context: LLMContext) -> None:
        """Extract usage stats and log/emit"""
        if not context.response:
            return
        
        usage = None
        if hasattr(context.response, "metadata") and context.response.metadata:
            usage = context.response.metadata.get("usage")
        elif hasattr(context.response, "usage"):
            usage = context.response.usage
        
        if usage:
            if hasattr(usage, 'to_dict'):
                usage_dict = usage.to_dict()
            elif isinstance(usage, dict):
                usage_dict = usage
            else:
                return
            
            prompt_tokens = usage_dict.get("prompt_tokens", 0)
            completion_tokens = usage_dict.get("completion_tokens", 0)
            total_tokens = usage_dict.get("total_tokens", prompt_tokens + completion_tokens)
            
            logger.info(
                f"Token usage - prompt: {prompt_tokens}, "
                f"completion: {completion_tokens}, "
                f"total: {total_tokens} "
                f"(model: {context.config.get('model', 'unknown')})"
            )
            
            context.metadata["usage"] = usage
