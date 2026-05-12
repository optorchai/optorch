"""LLM Context Lifecycle Handlers - Create context per node dispatch"""

from optorch.logging import get_logger
from typing import Any

from optorch.llm.lifecycle.context_factory import LLMContextFactory
from optorch.intents.base_intent_handler import BaseIntentHandler
from optorch.intents.intent_context import IntentContext

logger = get_logger(__name__)


class CreateLLMContext(BaseIntentHandler):
    """creates fresh LLMContext at PRE_DISPATCH"""
    
    async def execute(self, context: IntentContext) -> dict[str, Any]:
        """create LLMContext and attach to state
        
        Args:
            context: Intent context with data (state)
            
        Returns:
            Empty dict (no additional data)
        """
        node_context = None
        if hasattr(context.node, '_node_context'):
            node_context = context.node._node_context
        
        llm_context = LLMContextFactory.create(
            events=context.node.event_emitter,
            state=context.data,
            node_context=node_context
        )
        context.data._llm_context = llm_context
        return {}