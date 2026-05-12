"""
NodeContext - execution context for node operations.

Immutable container of service references passed through execution.
"""

from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass

if TYPE_CHECKING:
    from optorch.events.event_emitter import EventEmitter
    from optorch.session.session_manager import SessionManager
    from optorch.controller.node_controller import NodeController
    from optorch.history.manager import History
    from optorch.cache.manager import CacheManager
    from optorch.container import ApplicationContainer
    from optorch.state import BaseState


@dataclass
class NodeContext:
    """
    Execution context passed through node operations.
    
    Holds immutable service references. State passed separately.
    Follows existing pattern: IntentContext, LLMContext.
    
    Design:
    - NodeContext = immutable services (events, sessions, etc.)
    - State = mutable per-invocation data
    
    Usage:
        context = container.create_node_context(node="tariff")
        result = await controller.dispatch("tariff", state, context)
        context.events.emit("custom", {...})
    """
    controller: 'NodeController'
    events: 'EventEmitter'
    sessions: 'SessionManager'
    history: 'History'
    cache: 'CacheManager'
    container: 'ApplicationContainer'
    
    current_node_name: Optional[str] = None
    current_phase: Optional[str] = None
