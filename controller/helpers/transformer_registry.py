from typing import TYPE_CHECKING, Any

from optorch.transformers.transformer_registry import TransformerRegistry

if TYPE_CHECKING:
    from optorch.controller.node_controller import NodeController


class TransformerRegistryHelper:
    def __init__(self, controller: 'NodeController'):
        self._controller = controller
    
    def register(self, name: str, transformer: Any) -> None:
        self._controller._transformer_registry.register(name, transformer)

    def registry(self) -> TransformerRegistry:
        return self._controller._transformer_registry
