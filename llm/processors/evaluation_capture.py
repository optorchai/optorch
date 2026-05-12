"""
Evaluation capture processor - records LLM interactions for later evaluation.

POST_INVOKE hook that captures prompt/response pairs and optionally
sends them to Analytics for evaluation against test datasets.
"""
from optorch.logging import get_logger
from typing import Optional
from datetime import datetime

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext

logger = get_logger(__name__)


class EvaluationCaptureProcessor(BaseLLMProcessor):
    """
    Captures LLM prompt/response pairs for evaluation.
    
    POST_INVOKE stage - runs after LLM call completes.
    Non-blocking - failures logged but don't break LLM calls.
    """
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result", "retry"}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.POST_INVOKE
    
    async def process(self, context: LLMContext) -> None:
        """
        Capture LLM interaction data for evaluation.
        
        Stores:
        - Prompt text (from messages)
        - Model response
        - Node context
        - Timestamp metadata
        """
        eval_config = context.config.get("evaluation", {})
        
        if not eval_config.get("enabled", False):
            return
        
        if not eval_config.get("capture_responses", True):
            return
        
        prompt_text = self._extract_prompt_text(context)
        if not prompt_text:
            logger.debug("No prompt text found to capture")
            return
        
        if not context.response:
            logger.debug("No response found to capture")
            return
        
        response_text = context.response.content if hasattr(context.response, 'content') else str(context.response)
        
        prompt_name = context.metadata.get("prompt_name", "unknown")
        prompt_version = context.metadata.get("prompt_version", "unknown")
        
        context.processor_data["evaluation_data"] = {
            "prompt_name": prompt_name,
            "prompt_version": prompt_version,
            "prompt_text": prompt_text,
            "response_text": response_text,
            "model": context.config.get("model"),
            "timestamp": datetime.now().isoformat(),
            "session_id": context.metadata.get("session_id"),
            "node_name": context.metadata.get("node_name")
        }
        
        if eval_config.get("auto_submit", False):
            await self._submit_to_analytics(
                context=context,
                analytics_url=eval_config.get("analytics_url")
            )
        
        logger.debug(f"Captured evaluation data for {prompt_name} v{prompt_version}")
    
    def _extract_prompt_text(self, context: LLMContext) -> Optional[str]:
        """
        Extract prompt text from messages.
        
        Returns user message content or concatenated messages.
        """
        if not context.messages:
            return None
        
        for msg in context.messages:
            if isinstance(msg, dict) and msg.get("role") == "user":
                return msg.get("content", "")
        
        texts = []
        for msg in context.messages:
            if isinstance(msg, dict) and "content" in msg:
                texts.append(f"{msg.get('role', 'unknown')}: {msg['content']}")
        
        return "\n".join(texts) if texts else None
    
    async def _submit_to_analytics(
        self,
        context: LLMContext,
        analytics_url: Optional[str] = None
    ) -> None:
        """
        Submit captured data to Analytics for evaluation storage.
        
        Non-blocking - failures logged but don't break flow.
        """
        if not analytics_url:
            logger.debug("No analytics_url configured - skipping submission")
            return
        
        eval_data = context.processor_data.get("evaluation_data")
        if not eval_data:
            return
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{analytics_url}/evaluations/capture",
                    json={
                        "prompt_name": eval_data["prompt_name"],
                        "prompt_version": eval_data["prompt_version"],
                        "prompt_text": eval_data["prompt_text"],
                        "response_text": eval_data["response_text"],
                        "model": eval_data["model"],
                        "metadata": {
                            "session_id": eval_data.get("session_id"),
                            "node_name": eval_data.get("node_name"),
                            "timestamp": eval_data["timestamp"]
                        }
                    }
                )
                
                if response.status_code in [200, 201]:
                    logger.debug(f"Evaluation data submitted to Analytics: {response.json()}")
                else:
                    logger.warning(
                        f"Failed to submit evaluation data to Analytics: "
                        f"{response.status_code} - {response.text}"
                    )
        
        except Exception as e:
            logger.warning(f"Error submitting evaluation data to Analytics: {e}")
