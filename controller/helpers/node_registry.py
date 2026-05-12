from typing import TYPE_CHECKING, Type, Any, Optional, Dict
from optorch.controller.node_config import NodeConfig

if TYPE_CHECKING:
    from optorch.controller.node_controller import NodeController


class NodeRegistryHelper:
    def __init__(self, controller: 'NodeController'):
        self._controller = controller
    
    def register(self, name: str, node_class: Type[Any], config: Optional[Dict[str, Any]] = None) -> None:
        self._controller._node_registry.register(name, node_class)

        if config is not None:
            validated_config = NodeConfig(**config) if isinstance(config, dict) else config
            self._controller._node_configs.register(name, validated_config)

    def configure(self, name: str, config: Dict[str, Any]) -> None:
        validated_config = NodeConfig(**config) if isinstance(config, dict) else config
        self._controller._node_configs.register(name, validated_config)
