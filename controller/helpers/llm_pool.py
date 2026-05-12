from typing import TYPE_CHECKING, List

from optorch.llm.base_client import BaseLLMClient

if TYPE_CHECKING:
    from optorch.controller.node_controller import NodeController


class LLMPoolHelper:
    def __init__(self, controller: 'NodeController'):
        self._controller = controller
    
    def register(self, name: str, clients: List[BaseLLMClient], strategy: str = "round_robin") -> None:
        self._controller._llm_registry.register_pool(name, clients, strategy)
