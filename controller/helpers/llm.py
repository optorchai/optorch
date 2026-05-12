from typing import TYPE_CHECKING, Optional

from optorch.llm.base_client import BaseLLMClient
from optorch.llm.llm_registry import LLMRegistry
from optorch.controller.helpers.llm_pool import LLMPoolHelper

if TYPE_CHECKING:
    from optorch.controller.node_controller import NodeController


class LLMHelper:
    def __init__(self, controller: 'NodeController'):
        self._controller = controller
        self.pool = LLMPoolHelper(controller)
    
    def register(self, name: str, client: BaseLLMClient) -> None:
        self._controller._llm_registry.register(name, client)

    def get(self, name: str) -> Optional[BaseLLMClient]:
        return self._controller._llm_registry.get(name)

    def registry(self) -> LLMRegistry:
        return self._controller._llm_registry
