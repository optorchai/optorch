"""History retrieval processor - PRE_INVOKE"""

from optorch.logging import get_logger
from typing import Optional

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.events import emits, EventTypes

logger = get_logger(__name__)

class HistoryRetrieval(BaseLLMProcessor):
    """Retrieve conversation history before LLM invocation"""
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result", "retry"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.PRE_INVOKE
    
    @emits(EventTypes.HISTORY)
    async def process(self, context: LLMContext) -> Optional[list]:
        """Retrieve history and prepend to messages"""
        
        if not context.node_context or not context.node_context.history:
            logger.warning("History not initialized - skipping retrieval")
            return
        
        history = context.node_context.history
        
        session_id = "default"
        if context.state:
            session_id = context.state.get("session_id", "default")
        
        
        historical_messages = await history.get_messages(session_id)
        logger.info(f"🔍 HistoryRetrieval: retrieved {len(historical_messages)} messages from cache for session {session_id}")
        
        context.messages = historical_messages + context.messages
        context.processor_data["session_id"] = session_id
        
        return historical_messages
