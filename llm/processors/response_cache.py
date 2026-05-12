"""cache hit? skip llm call"""

import hashlib
import json
import time
from optorch.logging import get_logger
from typing import Dict, Optional, TYPE_CHECKING

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.events import EventTypes

if TYPE_CHECKING:
    from optorch.cache.manager import CacheManager

logger = get_logger(__name__)


class ResponseCache(BaseLLMProcessor):
    """cache hit? skip llm call"""
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self.exclude_substates = {"tool_result"}  # dont cache tools
        self._cache: Dict[str, Dict] = {}  # fallback if no manager
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.PRE_INVOKE
    
    async def process(self, context: LLMContext) -> None:
        """check cache before llm"""
        if not context.messages:
            logger.debug("No messages to cache - skipping")
            return
        
        # get ttl from config or whatever
        cache_config = context.config.get("cache", {}) if context.config else {}
        ttl = cache_config.get("ttl", 3600)
        
        cache_key = self._hash_messages(context.messages)
        context.metadata["cache_key"] = cache_key
        
        # try cache or fall back to crap memory
        cache = self._get_cache(context)
        
        if cache:
            cached_response = await self._get_from_cache(cache, cache_key, ttl)
        else:
            cached_response = self._get_from_memory_cache(cache_key, ttl)
        
        if cached_response:
            logger.info(f"Cache HIT: {cache_key[:8]}... (saved LLM call)")
            
            context.events.emit(f"{EventTypes.LLM}.cache.hit", {
                "cache_key": cache_key[:8],
                "response_content": cached_response.content if hasattr(cached_response, 'content') else str(cached_response),
                "timestamp": time.time()
            })
            
            context.response = cached_response
            context.skip_remaining = True
            context.metadata["cache_hit"] = True
        else:
            logger.debug(f"Cache MISS: {cache_key[:8]}...")
            
            context.events.emit(f"{EventTypes.LLM}.cache.miss", {
                "cache_key": cache_key[:8],
                "timestamp": time.time()
            })
            
            context.metadata["cache_hit"] = False
    
    def _get_cache(self, context: LLMContext) -> Optional['CacheManager']:
        """get cache manager or none"""
        try:
            if not context.node_context or not hasattr(context.node_context.container, 'cache_manager'):
                logger.warning("No cache manager available - skipping cache")
                return
            return context.node_context.container.cache_manager
        except Exception:
            return None
    
    async def _get_from_cache(self, cache: 'CacheManager', cache_key: str, ttl: int):
        """get from optorch cache"""
        try:
            cached_data = await cache.get(f"response:{cache_key}")
            if cached_data and isinstance(cached_data, dict):
                age = time.time() - cached_data.get("timestamp", 0)
                if age < ttl:
                    return cached_data["response"]
                else:
                    await cache.delete(f"response:{cache_key}")
            return None
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def _get_from_memory_cache(self, cache_key: str, ttl: int):
        """get from memory fallback"""
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            age = time.time() - cached_data["timestamp"]
            if age < ttl:
                return cached_data["response"]
            else:
                del self._cache[cache_key]
        return None
    
    def _hash_messages(self, messages: list) -> str:
        """hash without session junk"""
        normalized = []
        for msg in messages:
            if msg.get("role") == "system":
                continue
            
            normalized.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        message_str = json.dumps(normalized, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(message_str.encode()).hexdigest()