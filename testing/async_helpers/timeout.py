"""Async testing timeout utilities"""

import asyncio
from typing import Awaitable, TypeVar, Any, Callable
from functools import wraps

T = TypeVar('T')

DEFAULT_TIMEOUT = 5.0


class AsyncTimeout:
    """Context manager for async timeouts"""
    
    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self._task: Any = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._task and not self._task.done():
            self._task.cancel()
    
    async def run(self, coro: Awaitable[T]) -> T:
        """Run coroutine with timeout"""
        try:
            if hasattr(coro, '__await__'):
                self._task = asyncio.create_task(coro)  # type: ignore
            else:
                async def wrapper():
                    return coro  # type: ignore
                self._task = asyncio.create_task(wrapper())
            return await asyncio.wait_for(self._task, timeout=self.timeout)
        except asyncio.TimeoutError:
            raise AssertionError(f"Operation timed out after {self.timeout}s")


def timeout(seconds: float = DEFAULT_TIMEOUT):
    """Decorator for async test timeout"""
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async with AsyncTimeout(seconds) as ctx:
                return await ctx.run(func(*args, **kwargs))
        return wrapper
    return decorator