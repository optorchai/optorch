"""Transformer processor - POST_INVOKE message transformation"""

from optorch.logging import get_logger

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext

logger = get_logger(__name__)

class TransformerPipeline(BaseLLMProcessor):
    """Apply transformers to response content
    
    Non-streaming: Apply to final content immediately
    Streaming: Wrap stream with pattern accumulators for buffered application
    """
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.POST_INVOKE
    
    async def process(self, context: LLMContext) -> None:
        """Apply transformers to response"""
        transformer_names = context.config.get("transformers", [])
        if not transformer_names:
            logger.debug("No transformers configured")
            return
        
        if not context.response:
            logger.debug("No response - skipping transformers")
            return
        
        if not context.node_context:
            logger.warning("No node_context - cannot access transformers registry")
            return
        
        transformers = []
        for name in transformer_names:
            transformer = context.node_context.controller.transformers.registry().get(name)
            if transformer:
                transformers.append(transformer)
            else:
                logger.warning(f"Transformer {name} not found in registry")
        
        if not transformers:
            logger.debug("No valid transformers found")
            return
        
        logger.debug(f"Applying {len(transformers)} transformers")
        
        context.response = await context.response.apply_transformers(transformers, context)
        
        if context.response and context.response.metadata:
            context.metadata.update(context.response.metadata)
            logger.debug(f"Merged transformer metadata: {list(context.response.metadata.keys())}")
