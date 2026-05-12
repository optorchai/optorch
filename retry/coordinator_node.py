"""Retry-aware coordinator with escalation support"""
from optorch.logging import get_logger
from typing import Any, Optional
from optorch.nodes.coordinator_node import CoordinatorNode
from optorch.state import BaseState
from optorch.constants import StateKeys
from optorch.retry.escalation import EscalationFormatter

logger = get_logger(__name__)


class RetryCoordinator(CoordinatorNode):
    """
    Coordinator with built-in retry escalation support.
    
    Extends generic CoordinatorNode with escalation capabilities for when
    retry handlers exhaust all attempts and cannot auto-recover.
    
    Provides:
    - escalate() method for tone-aware user messaging
    - Automatic template loading with fragment injection
    - Resumption state management (PENDING_PHASE tracking)
    """
    
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        super().__init__(name, config)
        self._escalation_formatter = None
    
    @property
    def escalation_formatter(self) -> EscalationFormatter:
        """Lazy-load escalation formatter with prompt manager"""
        if self._escalation_formatter is None:
            self._escalation_formatter = EscalationFormatter(
                prompt_manager=self.prompt_manager
            )
        return self._escalation_formatter
    
    def escalate(
        self,
        state: BaseState,
        phase: str,
        template: str,
        error_key: str,
        context_key: Optional[str] = None
    ) -> BaseState:
        """
        Generic escalation handler with tone-aware messaging.
        
        Sets state for user escalation and resumption:
        - PENDING_PHASE: Which phase failed (for resumption routing)
        - PENDING_PHASE_CONTEXT: Error details and state snapshot
        - RESPONSE: Formatted user message with tone
        - NEEDS_USER_INPUT: Signal to return control to user
        
        Args:
            state: Current state
            phase: Phase name for resumption (e.g., "market_research")
            template: Template name (e.g., "market_research_failed")
            error_key: State key for error message (e.g., "market_research_error")
            context_key: Optional state key for additional context
        
        Returns:
            Updated state with escalation data
        """
        error = state.get(error_key, "Unknown error")
        context = state.get(context_key, "") if context_key else ""
        
        state[StateKeys.PENDING_PHASE] = phase
        state[StateKeys.PENDING_PHASE_CONTEXT] = {
            "error": error,
            "context": context,
            "characteristics": state.get("characteristics")
        }
        
        state[StateKeys.RESPONSE] = self.escalation_formatter.format(
            template,
            error=error,
            context=context
        )
        state[StateKeys.NEEDS_USER_INPUT] = True
        
        logger.info(f"Escalating {phase} failure to user: {error}")
        return state
