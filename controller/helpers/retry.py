from typing import TYPE_CHECKING, Any

from optorch.retry import RetryHandler as RetryHandlerCore

if TYPE_CHECKING:
    from optorch.controller.node_controller import NodeController


class RetryHelper:
    def __init__(self, controller: 'NodeController'):
        self._controller = controller
    
    def register_failure_type(self, name: str, handler: Any) -> None:
        """custom failure handler, for when things go sideways"""
        RetryHandlerCore.register_failure_type(name, handler)
