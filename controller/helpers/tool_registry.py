from typing import TYPE_CHECKING, Any

from optorch.tools.tool_registry import ToolRegistry

if TYPE_CHECKING:
    from optorch.controller.node_controller import NodeController


class ToolRegistryHelper:
    def __init__(self, controller: 'NodeController'):
        self._controller = controller
    
    def register(self, name: str, tool: Any) -> None:
        self._controller._tool_registry.register(name, tool)

    def registry(self) -> ToolRegistry:
        return self._controller._tool_registry
