from optorch.logging import get_logger
import inspect
from typing import Callable, Optional
from functools import wraps

from optorch.errors.handler import ErrorHandler, ErrorContext, ErrorAction


def error_context(
    component: Optional[str] = None,
    phase: Optional[str] = None,
    default_action: ErrorAction = ErrorAction.LOG_AND_RAISE
) -> Callable:
    # auto context detection from module/args
    def decorator(func: Callable) -> Callable:
        detected_component = component
        if not detected_component:
            module = func.__module__
            if module.startswith('app.'):
                detected_component = module.split('.')[1]
            elif module.startswith('optorch.'):
                detected_component = module.split('.')[1]
            else:
                detected_component = module.split('.')[0]
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                state = None
                for arg in args:
                    if hasattr(arg, 'get') and hasattr(arg, 'set'):
                        state = arg
                        break
                
                detected_phase = phase
                if not detected_phase and state and hasattr(state, '_current_phase'):
                    detected_phase = str(state._current_phase)
                
                from optorch.logging import get_logger
                logger = get_logger(func.__module__, detected_component)
                
                ctx = ErrorContext(
                    exception=e,
                    logger=logger,
                    state=state,
                    phase=detected_phase,
                    component=detected_component
                )
                ErrorHandler.handle(ctx, default_action)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                state = None
                for arg in args:
                    if hasattr(arg, 'get') and hasattr(arg, 'set'):
                        state = arg
                        break
                
                detected_phase = phase
                if not detected_phase and state and hasattr(state, '_current_phase'):
                    detected_phase = str(state._current_phase)
                
                from optorch.logging import get_logger
                logger = get_logger(func.__module__, detected_component)
                
                ctx = ErrorContext(
                    exception=e,
                    logger=logger,
                    state=state,
                    phase=detected_phase,
                    component=detected_component
                )
                ErrorHandler.handle(ctx, default_action)
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    if callable(component) and phase is None:
        func = component
        component = None
        return decorator(func)
    
    return decorator
