"""Core LLM invocation processor - executes actual LLM call"""

from optorch.logging import get_logger
from typing import Any

from optorch.llm.base_client import BaseLLMClient
from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.events.decorators import emits
from optorch.constants import EventTypes

logger = get_logger(__name__)

class LLMInvokeProcessor(BaseLLMProcessor):
    """Executes the core LLM invocation
    
    Runs during INVOKE phase - calls client with prepared messages.
    Only runs in default substate (not during tool execution).
    """
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.INVOKE
    
    @emits(EventTypes.ERROR)
    async def process(self, context: LLMContext) -> None:
        """Execute LLM invocation
        
        Args:
            context: LLM context with client, messages, config
            
        Side effects:
            Sets context.response with LLM response
        """
        if not context.config:
            logger.error("LLMInvokeProcessor: context.config is None")
            raise ValueError("context.config cannot be None")
            
        invoke_kwargs = context.config.get("invoke_kwargs", {})
        
        tools = invoke_kwargs.get("tools") if invoke_kwargs else None
        
        params = {
            "messages": context.messages,
            **invoke_kwargs
        }
        
        if tools:
            params["tools"] = tools
        
        logger.debug(
            f"Invoking LLM with {len(context.messages)} messages, "
            f"tools={bool(tools)}, streaming={context.streaming}"
        )
        
        if not context.client:
            raise RuntimeError("LLM client not available in context")
        
        if context.streaming:
            context.response = await context.client.astream(context, context.messages, **invoke_kwargs)
            if context.response and hasattr(context.response, 'set_context'):
                context.response.set_context(context)
        else:
            context.response = await context.client.invoke(context, context.messages, **invoke_kwargs)
        
        logger.debug(f"LLM response received: {bool(context.response)}")
