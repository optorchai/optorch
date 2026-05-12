import asyncio
from optorch.logging import get_logger
from typing import Any, Callable, Awaitable
from optorch.state import BaseState
from optorch.constants import RetryDefaults, ConfigKeys
from optorch.retry.failure_type_registry import FailureTypeRegistry
from optorch.nodes.base_node import BaseNode

logger = get_logger(__name__)


class RetryHandler:
    """LLMs lie sometimes, give them another shot"""
    
    _failure_registry = FailureTypeRegistry()
    
    @classmethod
    def register_failure_type(cls, name: str, handler):
        cls._failure_registry.register(name, handler)
    
    @classmethod
    async def execute_with_retry(
        cls, 
        node: BaseNode, 
        state: BaseState, 
        execute_fn: Callable[[BaseNode, BaseState], Awaitable[BaseState]], 
        config: dict[str, Any]
    ) -> BaseState:
        retry_config = config.get(ConfigKeys.RETRY, {})
        
        if not retry_config.get("enabled", False):
            return await execute_fn(node, state)
        
        max_attempts = retry_config.get("max_attempts", RetryDefaults.MAX_ATTEMPTS)
        backoff = retry_config.get("backoff_seconds", RetryDefaults.BACKOFF_SECONDS)
        on_failure = retry_config.get("on_failure", RetryDefaults.ON_FAILURE)
        
        for attempt in range(1, max_attempts + 1):
            result = await execute_fn(node, state)
            
            if not result.get("error"):
                if attempt > 1:
                    logger.info(f"{node.name} succeeded on attempt {attempt}")
                return result
            
            if attempt < max_attempts:
                logger.warning(f"{node.name} failed attempt {attempt}/{max_attempts}, retrying...")
                await asyncio.sleep(backoff)
                state.set("error", None)
            else:
                logger.error(f"{node.name} failed after {max_attempts} attempts")
                return cls._failure_registry.handle(on_failure, state, retry_config)
        
        return result
