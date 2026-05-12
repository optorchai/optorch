"""
Updated @emits decorator using context extraction.

Auto-emits start/complete/error events with timing.
"""

from typing import Callable, Any, TypeVar, overload, Awaitable, AsyncIterator
import time
import asyncio
from functools import wraps
from optorch.decorators.context_extraction import extract_context
from optorch.state import State
from optorch.llm.responses import LLMResponse

T = TypeVar('T')


@overload
def emits(event_prefix: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]: ...

@overload
def emits(event_prefix: str) -> Callable[[Callable[..., AsyncIterator[T]]], Callable[..., AsyncIterator[T]]]: ...

@overload
def emits(event_prefix: str) -> Callable[[Callable[..., T]], Callable[..., T]]: ...


def emits(event_prefix: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to auto-emit start/complete/error events.
    
    Extracts NodeContext from args/kwargs to access EventEmitter.
    If context not found, silently skips emission (useful for testing).
    
    Usage:
        # Node method
        class MyNode(StandardNode):
            @emits("node.operation")
            async def execute(self, state):
                # Extracts self.context
                pass
        
        # Tool
        @tool
        @emits("tool")
        async def my_tool(data: str, context: NodeContext):
            # Extracts context kwarg
            pass
        
        # Intent handler
        @emits("intent.execute")
        async def execute(self, intent_context: IntentContext):
            # Extracts intent_context.context
            pass
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        import inspect
        
        def make_serializable(obj: Any) -> Any:
            if isinstance(obj, State):
                return {"type": "State"}

            if isinstance(obj, LLMResponse):
                return {
                    "type": "LLMResponse",
                    "usage": obj.usage.to_dict() if obj.usage else None
                }
            
            if isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            
            if hasattr(obj, 'to_dict') and callable(obj.to_dict):
                return obj.to_dict()
            
            if hasattr(obj, '__dict__'):
                return {"type": obj.__class__.__name__}
            return obj
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            from optorch.logging import get_logger
            logger = get_logger(__name__)
            
            node_context = extract_context(args, kwargs)
            
            logger.error(f"[@emits {event_prefix}] CALLED - node_context={node_context is not None}, args_count={len(args)}")
            if len(args) > 1:
                logger.error(f"  args[1] type: {type(args[1]).__name__}, has node_context: {hasattr(args[1], 'node_context') if len(args) > 1 else False}")
            
            node_name: str | None = None
            if node_context and hasattr(node_context, 'current_node_name'):
                node_name = node_context.current_node_name
                logger.error(f"  Extracted node_name: {node_name}")
            
            start_time = time.time()
            
            if node_context and hasattr(node_context, 'events'):
                event_data: dict[str, Any] = {"node_name": node_name} if node_name else {}
                node_context.events.emit(f"{event_prefix}.start", event_data)
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                if node_context and hasattr(node_context, 'events'):
                    event_data: dict[str, Any] = {"duration_ms": duration_ms}
                    if node_name:
                        event_data["node_name"] = node_name
                    if result is not None:
                        event_data["result"] = make_serializable(result)
                    node_context.events.emit(f"{event_prefix}.complete", event_data)
                
                return result
            except Exception as e:
                if node_context and hasattr(node_context, 'events'):
                    error_data: dict[str, Any] = {"error": str(e)}
                    if node_name:
                        error_data["node_name"] = node_name
                    node_context.events.emit(f"{event_prefix}.error", error_data)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            node_context = extract_context(args, kwargs)
            
            if args and hasattr(args[0], 'node_context'):
                if not node_context:
                    node_context = args[0].node_context
            
            node_name: str | None = None
            if node_context and hasattr(node_context, 'current_node_name'):
                node_name = node_context.current_node_name
            
            start_time = time.time()
            
            if node_context and hasattr(node_context, 'events'):
                event_data: dict[str, Any] = {"node_name": node_name} if node_name else {}
                node_context.events.emit(f"{event_prefix}.start", event_data)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                if node_context and hasattr(node_context, 'events'):
                    event_data: dict[str, Any] = {
                        "duration_ms": duration_ms,
                        "result": make_serializable(result)
                    }
                    if node_name:
                        event_data["node_name"] = node_name
                    node_context.events.emit(f"{event_prefix}.complete", event_data)
                
                return result
            except Exception as e:
                if node_context and hasattr(node_context, 'events'):
                    error_data: dict[str, Any] = {"error": str(e)}
                    if node_name:
                        error_data["node_name"] = node_name
                    node_context.events.emit(f"{event_prefix}.error", error_data)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator
