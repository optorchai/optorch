"""Core message structure"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, Optional
from uuid import uuid4


@dataclass(slots=True)
class Message:
    
    role: str
    content: str
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "source": self.source
        }
    
    def to_llm_dict(self) -> Dict[str, str]:
        """LLM-compatible dict without internal fields (id, timestamp, metadata)"""
        return {
            "role": self.role,
            "content": self.content
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now(UTC)
        
        return cls(
            role=data["role"],
            content=data["content"],
            id=data.get("id", str(uuid4())),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
            source=data.get("source")
        )
    
    def __repr__(self) -> str:
        return f"Message(role={self.role}, id={self.id[:8]}...)"
