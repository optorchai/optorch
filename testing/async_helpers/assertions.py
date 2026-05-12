"""Async assertion helpers"""

import asyncio
from typing import Awaitable, Callable, TypeVar, Any

T = TypeVar('T')

POLL_INTERVAL = 0.1
DEFAULT_WAIT_TIMEOUT = 10.0


async def assert_eventually(
    condition: Callable[[], bool], 
    timeout: float = DEFAULT_WAIT_TIMEOUT,
    message: str = "Condition never became true"
) -> None:
    """Assert condition becomes true within timeout"""
    end_time = asyncio.get_event_loop().time() + timeout
    
    while asyncio.get_event_loop().time() < end_time:
        if condition():
            return
        await asyncio.sleep(POLL_INTERVAL)
    
    raise AssertionError(f"{message} (waited {timeout}s)")


async def wait_for_condition(
    condition: Callable[[], bool],
    timeout: float = DEFAULT_WAIT_TIMEOUT
) -> bool:
    """Wait for condition to become true, return success"""
    try:
        await assert_eventually(condition, timeout, "")
        return True
    except AssertionError:
        return False


async def assert_event_emitted(
    event_capture, 
    event_type: str,
    timeout: float = DEFAULT_WAIT_TIMEOUT,
    count: int = 1
) -> None:
    """Assert specific event was emitted"""
    await assert_eventually(
        lambda: event_capture.count(event_type) >= count,
        timeout,
        f"Event '{event_type}' not emitted {count} times"
    )