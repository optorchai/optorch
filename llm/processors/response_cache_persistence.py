"""store response after llm call"""

import time
from optorch.logging import get_logger
from typing import Dict

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.events import EventTypes

logger = get_logger(__name__)


class ResponseCachePersistence(BaseLLMProcessor):
    """store response after llm"""
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result"}
        self._cache: Dict[str, Dict] = {}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.POST_INVOKE
    
    async def process(self, context: LLMContext) -> None:
        """store if not from cache"""
        if context.metadata.get("cache_hit"):
            return
        
        cache_key = context.metadata.get("cache_key")
        if not cache_key or not context.response:
            return
        
        cache = self._get_cache(context)
        
        if cache:
            await self._store_in_cache(cache, cache_key, context.response)
        else:
            self._store_in_memory_cache(cache_key, context.response)
        
        logger.debug(f"Cache STORE: {cache_key[:8]}...")
        
        context.events.emit(f"{EventTypes.LLM}.cache.store", {
            "cache_key": cache_key[:8],
            "response_content": context.response.content if hasattr(context.response, 'content') else str(context.response),
            "timestamp": time.time()
        })
    
    def _get_cache(self, context: LLMContext):
        """get cache manager or none"""
        try:
            if not context.node_context or not hasattr(context.node_context.container, 'cache_manager'):
                logger.warning("No cache manager available - skipping cache")
                return
            return context.node_context.container.cache_manager
        except Exception:
            return None
    
    async def _store_in_cache(self, cache, cache_key: str, response):
        """store in optorch cache"""
        try:
            cache_data = {
                "response": response,
                "timestamp": time.time()
            }
            await cache.set(f"response:{cache_key}", cache_data)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def _store_in_memory_cache(self, cache_key: str, response):
        """store in memory fallback"""
        self._cache[cache_key] = {
            "response": response,
            "timestamp": time.time()
        }