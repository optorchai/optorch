from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from optorch.controller.node_controller import NodeController


class IntentRegistryHelper:
    def __init__(self, controller: 'NodeController'):
        self._controller = controller
    
    def register(self, name: str, handler: Any) -> None:
        self._controller._intent_registry.register(name, handler)
