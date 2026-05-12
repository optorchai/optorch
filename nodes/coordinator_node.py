"""Base coordinator node for orchestrating multi-phase workflows"""
from optorch.logging import get_logger
from abc import abstractmethod
from optorch.nodes.base_node import BaseNode
from optorch.state import BaseState

logger = get_logger(__name__)


class CoordinatorNode(BaseNode):
    """
    Base class for coordinator nodes that orchestrate multi-phase workflows.
    
    Coordinators manage complex workflows by:
    - Tracking phase completion states
    - Routing between child nodes
    - Handling parallel execution
    - Managing workflow state transitions
    
    For coordinators that need retry/escalation support, see RetryCoordinator
    in optorch.retry.coordinator_node.
    """
    
    @abstractmethod
    async def execute(self, state: BaseState) -> BaseState:
        """Execute coordinator workflow - must be implemented by subclass"""
        pass
