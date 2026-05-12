import time
from enum import Enum
from typing import Optional, Callable, Union, Dict, Protocol, Any, cast, TYPE_CHECKING
from dataclasses import dataclass

from optorch.errors.exceptions import OptorchError
from optorch.logging import ContextLogger
from optorch.types import ToolResult

if TYPE_CHECKING:
    from optorch.events.event_emitter import EventEmitter

SESSION_ID_LENGTH = 8


class StateProtocol(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> 'StateProtocol': ...


class ErrorAction(Enum):
    RAISE = "raise"
    LOG = "log"
    EMIT = "emit"
    LOG_AND_RAISE = "log_and_raise"
    EMIT_AND_RAISE = "emit_and_raise"
    EMIT_AND_LOG = "emit_and_log"
    FATAL = "fatal"


@dataclass
class ErrorContext:
    exception: Exception
    logger: ContextLogger
    state: Optional[Union[Dict, StateProtocol]] = None
    phase: Optional[str] = None
    session_id: Optional[str] = None
    component: Optional[str] = None
    event_emitter: Optional["EventEmitter"] = None
    
    def get_session_id(self) -> Optional[str]:
        if self.session_id:
            return self.session_id
        if self.state and hasattr(self.state, 'get'):
            return self.state.get('session_id')
        return None


class ErrorHandler:
    # central error orchestration
    
    _policy: Dict[str, ErrorAction] = {}
    _emit_policy: Dict[str, bool] = {}
    _log_levels: Dict[str, str] = {}
    _fatal_handlers: Dict[str, Callable] = {}
    _emit_events: bool = True
    _severity_map: Dict[str, str] = {
        "ValidationError": "low",
        "ToolExecutionError": "medium",
        "ProcessorError": "medium",
        "StateError": "medium",
        "LLMError": "high",
        "SessionError": "high",
        "ConfigurationError": "critical"
    }
    
    @classmethod
    def configure(
        cls,
        policy: Optional[Dict[str, str]] = None,
        emit_events: bool = True,
        emit_policy: Optional[Dict[str, bool]] = None,
        log_levels: Optional[Dict[str, str]] = None,
        fatal_handlers: Optional[Dict[str, Callable]] = None,
        severity_map: Optional[Dict[str, str]] = None
    ) -> None:
        if policy:
            cls._policy = {
                exc_name: ErrorAction(action)
                for exc_name, action in policy.items()
            }
        
        cls._emit_events = emit_events
        
        if emit_policy:
            cls._emit_policy = emit_policy
        
        if log_levels:
            cls._log_levels = log_levels
        
        if fatal_handlers:
            cls._fatal_handlers = fatal_handlers
        
        if severity_map:
            cls._severity_map.update(severity_map)
    
    @classmethod
    def handle(cls, ctx: ErrorContext, default_action: ErrorAction = ErrorAction.LOG_AND_RAISE) -> None:
        exc = ctx.exception
        exc_type = type(exc).__name__
        
        action = cls._policy.get(exc_type, default_action)
        
        cls._log_error(ctx, exc_type)
        
        if cls._should_emit(exc_type):
            cls._emit_error_event(ctx, exc_type)
        
        if ctx.state:
            cls._update_state(ctx)
        
        if action == ErrorAction.FATAL:
            cls._handle_fatal(ctx, exc_type)
            return
        
        if action in (ErrorAction.RAISE, ErrorAction.LOG_AND_RAISE, ErrorAction.EMIT_AND_RAISE):
            raise exc
    
    @classmethod
    def capture(
        cls,
        message: str,
        state: Optional[Union[Dict, StateProtocol]] = None,
        details: Optional[Dict] = None,
        error_type: str = "ValidationError",
        component: Optional[str] = None,
        phase: Optional[str] = None,
        return_dict: bool = False
    ) -> Optional[ToolResult]:
        from optorch.logging import get_logger
        
        logger = get_logger(__name__, component)
        
        from optorch.errors.exceptions import ValidationError, OptorchError
        exc_class = globals().get(error_type)
        if not exc_class or not issubclass(exc_class, Exception):
            exc: Exception = ValidationError(message, details=details)
        elif issubclass(exc_class, OptorchError):
            exc = exc_class(message, details=details)
        else:
            exc = exc_class(message)
        
        ctx = ErrorContext(
            exception=exc,
            logger=logger,
            state=state,
            phase=phase,
            component=component
        )
        
        try:
            cls.handle(ctx, default_action=ErrorAction.EMIT_AND_LOG)
        except:
            pass
        
        if return_dict:
            return {
                "success": False,
                "error": message,
                "error_type": error_type,
                "details": details or {}
            }
        
        return None
    
    @classmethod
    def _log_error(cls, ctx: ErrorContext, exc_type: str) -> None:
        session_id = ctx.get_session_id()
        prefix_parts = []
        
        if session_id:
            prefix_parts.append(f"[{session_id[:SESSION_ID_LENGTH]}]")
        if ctx.component:
            prefix_parts.append(f"[{ctx.component}]")
        if ctx.phase:
            prefix_parts.append(f"[{ctx.phase}]")
        
        prefix = " ".join(prefix_parts)
        msg = f"{prefix} {ctx.exception}" if prefix else str(ctx.exception)
        
        log_level = cls._log_levels.get(exc_type, "error")
        log_fn = getattr(ctx.logger, log_level, ctx.logger.error)
        
        extra = {}
        if isinstance(ctx.exception, OptorchError):
            extra['error_details'] = ctx.exception.details
        if exc_type:
            extra['error_type'] = exc_type
        
        log_fn(msg, exc_info=True, extra=extra)
    
    @classmethod
    def _should_emit(cls, exc_type: str) -> bool:
        if not cls._emit_events:
            return False
        
        return cls._emit_policy.get(exc_type, True)
    
    @classmethod
    def _emit_error_event(cls, ctx: ErrorContext, exc_type: str) -> None:
        if not ctx.event_emitter:
            return
        
        try:
            from optorch.events.event_types import EventTypes
            
            severity = cls._get_severity(exc_type, ctx.exception)
            
            ctx.event_emitter.emit(EventTypes.ERROR, {
                "error": str(ctx.exception),
                "error_type": exc_type,
                "session_id": ctx.get_session_id(),
                "phase": ctx.phase,
                "component": ctx.component,
                "severity": severity,
                "details": getattr(ctx.exception, 'details', None),
                "timestamp": time.time()
            })
        except Exception as e:
            if hasattr(ctx.logger, 'warning'):
                ctx.logger.warning(f"Failed to emit error event: {e}")
    
    @classmethod
    def _get_severity(cls, exc_type: str, exc: Exception) -> str:
        if isinstance(exc, OptorchError):
            return exc.severity
        
        return cls._severity_map.get(exc_type, "medium")
    
    @classmethod
    def _update_state(cls, ctx: ErrorContext) -> None:
        try:
            if ctx.state is None:
                return
            
            if hasattr(ctx.state, 'set') and callable(getattr(ctx.state, 'set')):
                state_obj = cast(StateProtocol, ctx.state)
                state_obj.set("error", str(ctx.exception))
                state_obj.set("error_type", type(ctx.exception).__name__)
            elif isinstance(ctx.state, dict):
                ctx.state["error"] = str(ctx.exception)
                ctx.state["error_type"] = type(ctx.exception).__name__
        except Exception:
            pass
    
    @classmethod
    def _handle_fatal(cls, ctx: ErrorContext, exc_type: str) -> None:
        handler = cls._fatal_handlers.get(exc_type)
        
        if handler:
            try:
                handler(ctx)
            except Exception as e:
                ctx.logger.critical(f"Fatal handler failed: {e}", exc_info=True)
        
        ctx.logger.critical(f"Fatal error, shutting down: {ctx.exception}", exc_info=True)
        raise SystemExit(1)

