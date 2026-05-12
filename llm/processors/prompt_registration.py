"""Prompt registration processor - auto-register prompts to Analytics on first use"""

import hashlib
from optorch.logging import get_logger
from typing import Optional
from datetime import datetime

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext

logger = get_logger(__name__)


class PromptRegistration(BaseLLMProcessor):
    """
    Auto-register prompts to Analytics registry on first LLM call.
    
    Extracts system message, generates hash-based version, stores metadata
    for Analytics API consumption. Non-blocking - failures don't break LLM calls.
    """
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result", "retry"}
        self._analytics_url: Optional[str] = None
        self._enabled = False
        self._version_strategy = "hash"
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.PRE_INVOKE
    
    async def process(self, context: LLMContext) -> None:
        """Register prompt if auto-registration enabled"""
        reg_config = context.config.get("prompt_registration", {})
        
        if not reg_config.get("auto_register", False):
            logger.debug("Prompt auto-registration disabled")
            return
        
        if not context.messages or len(context.messages) == 0:
            logger.debug("No messages - skipping prompt registration")
            return
        
        first_message = context.messages[0]
        if first_message.get("role") != "system":
            logger.debug("First message not system prompt - skipping registration")
            return
        
        prompt_content = first_message.get("content", "")
        if not prompt_content:
            logger.debug("Empty system prompt - skipping registration")
            return
        
        prompt_name = context.metadata.get("prompt_name")
        if not prompt_name:
            prompt_name = context.config.get("prompt_name")
        if not prompt_name:
            if context.node_context and hasattr(context.node_context, "current_node_name"):
                prompt_name = context.node_context.current_node_name or "unnamed"
            else:
                prompt_name = "unnamed"
        
        version_strategy = reg_config.get("version_strategy", "hash")
        analytics_url = reg_config.get("analytics_url")
        
        if version_strategy == "hash":
            prompt_hash = hashlib.sha256(prompt_content.encode()).hexdigest()[:16]
            version = f"auto_{prompt_hash}"
        elif version_strategy == "timestamp":
            version = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            version = context.metadata.get("prompt_version", "v1.0")
        
        context.metadata["prompt_name"] = prompt_name
        context.metadata["prompt_version"] = version
        context.processor_data["prompt_registered"] = True
        
        await self._register_with_analytics(
            prompt_name=prompt_name,
            version=version,
            content=prompt_content,
            metadata={
                "auto_registered": True,
                "node_name": context.config.get("node_name"),
                "model": context.config.get("model"),
                "version_strategy": version_strategy,
                "timestamp": datetime.now().isoformat()
            },
            analytics_url=analytics_url
        )
        
        logger.debug(f"Prompt registered: {prompt_name} v{version}")
    
    async def _register_with_analytics(
        self,
        prompt_name: str,
        version: str,
        content: str,
        metadata: dict,
        analytics_url: Optional[str] = None
    ) -> None:
        """
        Call Analytics API to register prompt.
        
        Non-blocking - failures logged but don't break LLM calls.
        """
        if not analytics_url:
            logger.debug("No analytics_url configured - skipping API call")
            return
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{analytics_url}/prompts/",
                    json={
                        "name": prompt_name,
                        "version": version,
                        "content": content,
                        "metadata": metadata
                    }
                )
                
                if response.status_code in [200, 201, 409]:
                    logger.debug(f"Prompt registered with Analytics: {prompt_name} v{version}")
                else:
                    logger.warning(f"Analytics registration failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.warning(f"Prompt registration failed (non-critical): {e}")
