from abc import ABC, abstractmethod
from typing import Any
from .intent_context import IntentContext


class BaseIntentHandler(ABC):
    @abstractmethod
    async def execute(self, context: IntentContext) -> dict[str, Any]:
        pass
    
    def should_execute(self, context: IntentContext) -> bool:
        return True
