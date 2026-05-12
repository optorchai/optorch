"""Runtime message context"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from .message import Message


@dataclass(slots=True)
class MessageContext:
    
    session_id: str
    user_id: Optional[str] = None
    filters: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    limit: Optional[int] = None
    
    def apply_limit(self, messages: List[Message]) -> List[Message]:
        if self.limit and len(messages) > self.limit:
            return messages[-self.limit:]
        return messages
