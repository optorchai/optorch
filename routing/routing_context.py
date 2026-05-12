from typing import Any
from dataclasses import dataclass, field
from optorch.state import BaseState


@dataclass
class RoutingContext:
    current_node: str
    result: BaseState
    history: list[str] = field(default_factory=list)
    return_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_to_history(self, node_name: str) -> None:
        self.history.append(node_name)
    
    def with_return(self, node_name: str) -> "RoutingContext":
        self.return_to = node_name
        return self
