"""Message builder processor - constructs messages from state and prompts"""

from typing import Optional, Set
from optorch.logging import get_logger

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext

logger = get_logger(__name__)

class MessageBuilder(BaseLLMProcessor):
    """Builds initial messages from state and configured prompts
    
    Runs in PRE_INVOKE before history retrieval to construct current turn messages.
    Loads system prompt from prompt_manager, extracts user message from state.
    """
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.PRE_INVOKE
    
    async def process(self, context: LLMContext) -> None:
        """Build messages from state and prompts"""
        if not context.state:
            logger.debug("No state provided - skipping message building")
            return
        
        messages_start_count = len(context.messages) if context.messages else 0
        
        prompts = context.config.get("prompts", {}) if context.config else {}
        prompt_manager = context.config.get("prompt_manager") if context.config else None
        
        if prompts and prompts.get("system") and prompt_manager:
            try:
                system_prompt = await prompt_manager.load_prompt(prompts["system"])
                if system_prompt:
                    context.messages.append({
                        "role": "system",
                        "content": system_prompt
                    })
                    logger.debug(f"Added system prompt from {prompts['system']}")
            except Exception as e:
                logger.warning(f"Failed to load system prompt: {e}")
        
        state_messages = context.state.get_messages()
        for msg in state_messages:
            context.messages.append(msg.to_llm_dict())
            logger.debug(f"Added message from state: {msg.role}")
        
        user_message = context.state.get("user_message")
        if user_message:
            messages_added_this_turn = context.messages[messages_start_count:]
            has_user_this_turn = any(m.get("role") == "user" for m in messages_added_this_turn)
            if not has_user_this_turn:
                context.messages.append({
                    "role": "user",
                    "content": user_message
                })
                logger.debug("Added user message from state")
        
        logger.debug(f"Built {len(context.messages)} messages for current turn")
