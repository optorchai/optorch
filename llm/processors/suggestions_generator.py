"""Suggestions generator processor - runs after history persistence"""
from optorch.logging import get_logger
import json

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.events.event_types import EventTypes

logger = get_logger(__name__)


class SuggestionsGenerator(BaseLLMProcessor):
    """Generate contextual follow-up suggestions after conversation persisted"""
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.FINALIZE
    
    async def process(self, context: LLMContext) -> None:
        """Generate suggestions using conversation history - non-blocking"""
        
        if not context.state or not context.state.get("suggestions"):
            return
        
        import asyncio
        task = asyncio.create_task(self._generate_suggestions(context))
        context.register_pending_task(task, "suggestions_generation")
    
    async def _generate_suggestions(self, context: LLMContext) -> None:
        """Background task for generating suggestions"""
        
        if not context.state:
            logger.warning("No state in suggestions background task")
            return
        
        if not context.node_context:
            logger.warning("No node_context - cannot access history")
            return
        
        config_manager = context.node_context.container.config_manager
        suggestions_config = config_manager.get("optorch.llm.suggestions", {})
        
        if not suggestions_config:
            logger.debug("Suggestions not configured in llm.suggestions")
            return
        
        session_id = context.state.get("session_id")
        if not session_id:
            return
        
        try:
            history = context.node_context.history
            if not history:
                logger.warning("History not initialized")
                return
            
            messages = await history.get_messages(session_id)
            messages = messages[-4:]
            
            if len(messages) < 2:
                return
            
            count = suggestions_config.get("count", 3)
            llm_model = suggestions_config.get("model", "fast")
            
            prompt_context = "\n".join([
                f"{m['role']}: {m['content']}" 
                for m in messages 
                if m.get('content')
            ])
            
            prompt_mgr = context.node_context.controller._prompt_manager
            if not prompt_mgr:
                logger.warning("PromptManager not initialized")
                return
            
            template = await prompt_mgr.load_prompt("helpers/suggestions")
            
            if not template:
                logger.warning("suggestions prompt template not found")
                return
            
            prompt = template.replace("{context}", prompt_context).replace("{count}", str(count))
            
            if not context.node_context or not context.node_context.container.llm_manager:
                logger.warning("No LLMManager available - skipping suggestions")
                return
            
            llm = context.node_context.container.llm_manager
            
            from optorch.state import StateFactory
            suggestions_state = StateFactory.create({"session_id": context.state.get("session_id")})
                        
            response = await llm.invoke(
                model=llm_model, 
                messages=[{"role": "user", "content": prompt}], 
                config={
                    "transformers": [],
                    "_budget_config": None,
                    "suggestions": False
                },
                state=suggestions_state,
                event_emitter=context.events, 
                node_context=context.node_context
            )
            
            content = response.content
            if not content:
                logger.warning("LLM returned empty content")
                return
            
            content = content.strip()
            if "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith("json\n"):
                        content = content[5:]
            
            suggestions = json.loads(content)
            context.processor_data["suggestions"] = suggestions[:count]
                        
            context.events.emit(EventTypes.SUGGESTIONS, {
                "suggestions": suggestions[:count],
                "session_id": session_id
            })
            
        except Exception as e:
            logger.error(f"❌ Suggestion generation failed: {e}", exc_info=True)
