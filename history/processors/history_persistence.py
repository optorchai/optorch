"""History persistence processor"""

from optorch.logging import get_logger
from typing import Dict, Any, List, TYPE_CHECKING

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.messaging import MessageContext, Message

if TYPE_CHECKING:
    from optorch.history.manager import History

logger = get_logger(__name__)

class HistoryPersistence(BaseLLMProcessor):
    """Persist conversation after LLM response"""
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.FINALIZE
    
    async def process(self, context: LLMContext) -> None:
        """Save conversation to history storage"""
        
        if not context.node_context or not context.node_context.history:
            return
        
        history: 'History' = context.node_context.history
        session_id = context.processor_data.get("session_id", "default")
        
        logger.info(f"💾 HistoryPersistence: session_id={session_id}, saving conversation")
        
        messages: List[Message] = []
        
        if context.messages:
            user_msg = context.messages[-1]
            messages.append(Message(
                role=user_msg.get("role", "user"),
                content=user_msg.get("content", ""),
                metadata={}
            ))
        
        if context.response and context.response.content:
            metadata: Dict[str, Any] = {}
            if context.response.tool_calls:
                metadata["tool_calls"] = context.response.tool_calls
            
            messages.append(Message(
                role="assistant",
                content=context.response.content,
                metadata=metadata
            ))
        
        if messages:
            logger.debug(f"Persisting {len(messages)} messages to history (session_id={session_id})")
            await history.save(messages, MessageContext(session_id=session_id))
        else:
            logger.warning("No messages to persist")
