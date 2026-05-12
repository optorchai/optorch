from typing import Any, Optional
from dataclasses import dataclass, field
from optorch.state import BaseState


@dataclass
class IntentContext:
    node: Any
    operation: str
    data: BaseState
    metadata: dict[str, Any] = field(default_factory=dict)
    skip_execution: bool = False
    result: Optional[BaseState] = None
    
    def with_data(self, **kwargs) -> "IntentContext":
        self.data.update(kwargs)
        return self
    
    def with_metadata(self, **kwargs) -> "IntentContext":
        self.metadata.update(kwargs)
        return self
