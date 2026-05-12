from optorch.logging import get_logger
from typing import Callable, Dict, Any
from optorch.state import BaseState
from optorch.constants import FailureType

logger = get_logger(__name__)


class FailureTypeRegistry:
    """Custom failure handlers, because LLMs need babysitting"""
    
    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[[BaseState, dict[str, Any]], BaseState]] = {}
        self._register_defaults()
    
    def register(self, name: str, handler: Callable[[BaseState, dict[str, Any]], BaseState]) -> None:
        self._handlers[name] = handler
    
    def handle(self, failure_type: str, state: BaseState, config: dict[str, Any]) -> BaseState:
        handler = self._handlers.get(failure_type)
        if not handler:
            logger.warning(f"Unknown failure type '{failure_type}', halting")
            return state
        
        return handler(state, config)
    
    def _register_defaults(self) -> None:
        self.register(FailureType.HALT, self._halt)
        self.register(FailureType.USE_DEFAULTS, self._use_defaults)
        self.register(FailureType.SKIP, self._skip)
        self.register(FailureType.FALLBACK, self._fallback)
        self.register(FailureType.ESCALATE, self._escalate)
    
    @staticmethod
    def _halt(state: BaseState, config: dict[str, Any]) -> BaseState:
        return state
    
    @staticmethod
    def _use_defaults(state: BaseState, config: dict[str, Any]) -> BaseState:
        default = config.get("default_value", {})
        for key, value in default.items():
            state.set(key, value)
        state.set("error", None)
        logger.info("Using defaults after failure")
        return state
    
    @staticmethod
    def _skip(state: BaseState, config: dict[str, Any]) -> BaseState:
        state.set("error", None)
        logger.info("Skipping failed node")
        return state
    
    @staticmethod
    def _fallback(state: BaseState, config: dict[str, Any]) -> BaseState:
        fallback = config.get("fallback_node")
        state.set("_retry_fallback", fallback)
        state.set("error", None)
        logger.info(f"Falling back to {fallback}")
        return state
    
    @staticmethod
    def _escalate(state: BaseState, config: dict[str, Any]) -> BaseState:
        message = config.get("escalation_message", "Node failed, need help")
        state.set("response", message.format(last_error=state.get("error")))
        state.set("error", None)
        state.set("_needs_user_input", True)
        logger.info("Escalating to user")
        return state
