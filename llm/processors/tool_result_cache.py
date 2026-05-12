"""tool result cache - dont execute twice"""

import hashlib
import json
import time
from optorch.logging import get_logger
from typing import Dict, Optional, TYPE_CHECKING, Any

from optorch.llm.lifecycle.base_processor import BaseLLMProcessor
from optorch.llm.lifecycle.hooks import LLMLifecycleHook
from optorch.llm.lifecycle.context import LLMContext
from optorch.events import EventTypes

if TYPE_CHECKING:
    from optorch.controller.node_context import NodeContext
    from optorch.container import ApplicationContainer
    from optorch.tools.tool_registry import ToolRegistry

logger = get_logger(__name__)


class ToolResultCache(BaseLLMProcessor):
    """cache tool results - dont execute twice"""
    
    def __init__(self):
        super().__init__()
        self.substates = {"default"}
        self._cache: Dict[str, Dict] = {}
    
    @property
    def hook(self) -> LLMLifecycleHook:
        return LLMLifecycleHook.TOOL_EXECUTION
    
    def should_run(self, context: LLMContext) -> bool:
        """run for non-streaming only"""
        return not context.streaming and super().should_run(context)
    
    async def process(self, context: LLMContext) -> None:
        """intercept tool execution and check cache"""
        if not context.response or not context.response.tool_calls:
            logger.debug("No tool calls to cache")
            return
        
        cache_config = context.config.get("tool_cache", {}) if context.config else {}
        ttl = cache_config.get("ttl", 1800)
        
        tool_calls = context.response.tool_calls
        cached_results = []
        uncached_calls = []
        
        for tool_call in tool_calls:
            tool_name = self._extract_tool_name(tool_call)
            args = self._extract_args(tool_call)
            tool_id = self._extract_tool_id(tool_call)
            
            cache_key = self._hash_tool_call(tool_name, args)
            
            cache = self._get_cache(context)
            cached_result = await self._get_cached_result(cache, cache_key, ttl)
            
            if cached_result:
                logger.info(f"Tool cache HIT: {tool_name}({cache_key[:8]}...)")
                
                context.events.emit(f"{EventTypes.TOOL}.cache.hit", {
                    "tool_name": tool_name,
                    "cache_key": cache_key[:8],
                    "result": cached_result,
                    "timestamp": time.time()
                })
                
                cached_results.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": cached_result
                })
            else:
                logger.debug(f"Tool cache MISS: {tool_name}({cache_key[:8]}...)")
                
                context.events.emit(f"{EventTypes.TOOL}.cache.miss", {
                    "tool_name": tool_name,
                    "cache_key": cache_key[:8],
                    "timestamp": time.time()
                })
                
                uncached_calls.append({
                    "call": tool_call,
                    "cache_key": cache_key,
                    "tool_name": tool_name,
                    "args": args
                })
        
        if cached_results and not uncached_calls:
            logger.info(f"All {len(tool_calls)} tools cached - skipping execution")
            context.messages.extend(cached_results)
            context.metadata["all_tools_cached"] = True
            return
        
        if uncached_calls:
            executed_results = await self._execute_uncached_tools(uncached_calls, context)
            
            all_results = cached_results + executed_results
            context.messages.extend(all_results)
            
            await self._cache_new_results(uncached_calls, executed_results, context)
    
    async def _execute_uncached_tools(self, uncached_calls: list, context: LLMContext) -> list:
        """execute tools that werent cached"""
        results = []
        
        for call_data in uncached_calls:
            tool_call = call_data["call"]
            tool_name = call_data["tool_name"]
            args = call_data["args"]
            tool_id = self._extract_tool_id(tool_call)
            
            try:
                logger.debug(f"Executing uncached tool: {tool_name}")
                
                node_ctx: Optional['NodeContext'] = context.node_context
                if not node_ctx or not hasattr(node_ctx.container, 'tool_registry'):
                    raise ValueError("No tool registry available in context")
                    
                container: 'ApplicationContainer' = node_ctx.container
                if container.tool_registry is None:
                    raise ValueError("Tool registry not initialized in container")
                    
                tool_registry: 'ToolRegistry' = container.tool_registry
                result: Any = await tool_registry.execute(tool_name=tool_name, **args)
                
                result_str = json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                
                results.append({
                    "role": "tool", 
                    "tool_call_id": tool_id,
                    "content": result_str
                })
                
                call_data["result"] = result_str
                
            except Exception as e:
                logger.error(f"Tool execution failed: {tool_name}: {e}")
                error_result = f"Error: {str(e)}"
                
                results.append({
                    "role": "tool",
                    "tool_call_id": tool_id, 
                    "content": error_result
                })
                
                call_data["result"] = error_result
        
        return results
    
    async def _cache_new_results(self, uncached_calls: list, executed_results: list, context: LLMContext):
        """cache newly executed results"""
        cache = self._get_cache(context)
        
        for call_data in uncached_calls:
            cache_key = call_data["cache_key"]
            result = call_data.get("result")
            tool_name = call_data["tool_name"]
            
            if result:
                await self._store_result(cache, cache_key, result)
                
                context.events.emit(f"{EventTypes.TOOL}.cache.store", {
                    "tool_name": tool_name,
                    "cache_key": cache_key[:8],
                    "result": result,
                    "timestamp": time.time()
                })
    
    async def _get_cached_result(self, cache, cache_key: str, ttl: int) -> Optional[str]:
        """get result from cache if fresh"""
        if cache:
            return await self._get_from_cache_manager(cache, cache_key, ttl)
        else:
            return self._get_from_memory_cache(cache_key, ttl)
    
    async def _get_from_cache_manager(self, cache, cache_key: str, ttl: int) -> Optional[str]:
        """get from optorch cache"""
        try:
            cached_data = await cache.get(f"tool:{cache_key}")
            if cached_data and isinstance(cached_data, dict):
                age = time.time() - cached_data.get("timestamp", 0)
                if age < ttl:
                    return cached_data["result"]
                else:
                    await cache.delete(f"tool:{cache_key}")
            return None
        except Exception as e:
            logger.warning(f"Tool cache read error: {e}")
            return None
    
    def _get_from_memory_cache(self, cache_key: str, ttl: int) -> Optional[str]:
        """fallback memory cache"""
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            age = time.time() - cached_data["timestamp"]
            if age < ttl:
                return cached_data["result"]
            else:
                del self._cache[cache_key]
        return None
    
    async def _store_result(self, cache, cache_key: str, result: str):
        """store result in cache"""
        cache_data = {
            "result": result,
            "timestamp": time.time()
        }
        
        if cache:
            try:
                await cache.set(f"tool:{cache_key}", cache_data)
            except Exception as e:
                logger.warning(f"Tool cache write error: {e}")
                self._cache[cache_key] = cache_data
        else:
            self._cache[cache_key] = cache_data
    
    def _get_cache(self, context: LLMContext):
        """get cache manager"""
        try:
            node_ctx: Optional['NodeContext'] = context.node_context
            if not node_ctx or not hasattr(node_ctx.container, 'cache_manager'):
                logger.warning("No cache manager available - skipping cache")
                return
            return node_ctx.container.cache_manager
        except Exception:
            return None
    
    def _extract_tool_name(self, tool_call) -> str:
        """extract tool name from call"""
        if isinstance(tool_call, dict):
            return tool_call.get("function", {}).get("name", "unknown")
        else:
            return tool_call.function.name
    
    def _extract_args(self, tool_call) -> dict:
        """extract args from call"""
        if isinstance(tool_call, dict):
            args_str = tool_call.get("function", {}).get("arguments", "{}")
        else:
            args_str = tool_call.function.arguments
        
        try:
            return json.loads(args_str) if isinstance(args_str, str) else args_str
        except Exception:
            return {}
    
    def _extract_tool_id(self, tool_call) -> str:
        """extract tool id from call"""
        if isinstance(tool_call, dict):
            return tool_call.get("id", "unknown")
        else:
            return tool_call.id
    
    def _hash_tool_call(self, tool_name: str, args: dict) -> str:
        """hash tool call for caching"""
        normalized_args = json.dumps(args, sort_keys=True, separators=(',', ':'))
        call_str = f"{tool_name}:{normalized_args}"
        return hashlib.sha256(call_str.encode()).hexdigest()