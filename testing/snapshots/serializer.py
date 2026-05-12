"""Snapshot serialization for complex objects"""

import json
from decimal import Decimal
from typing import Any, Dict, List
from datetime import datetime
from dataclasses import is_dataclass, asdict

from optorch.llm.responses.standard_response import StandardLLMResponse
from optorch.state.base_state import BaseState


class SnapshotSerializer:
    """Serializes objects for snapshot comparison"""
    
    def serialize(self, obj: Any) -> Any:
        """Convert object to JSON-serializable form"""
        if obj is None:
            return None
        
        if isinstance(obj, (str, int, float, bool)):
            return obj
        
        if isinstance(obj, Decimal):
            return f"Decimal('{obj}')"
        
        if isinstance(obj, datetime):
            return f"datetime('{obj.isoformat()}')"
        
        if isinstance(obj, dict):
            return {k: self.serialize(v) for k, v in obj.items()}
        
        if isinstance(obj, (list, tuple)):
            return [self.serialize(item) for item in obj]
        
        if is_dataclass(obj) and not isinstance(obj, type):
            return {
                "__type__": obj.__class__.__name__,
                **{k: self.serialize(v) for k, v in asdict(obj).items()}
            }
        
        if isinstance(obj, StandardLLMResponse):
            return {
                "__type__": "StandardLLMResponse",
                "content": obj.content,
                "tool_calls": self.serialize(obj.tool_calls),
                "usage": self.serialize(obj.usage),
                "metadata": self.serialize(obj.metadata)
            }
        
        if isinstance(obj, BaseState):
            return {
                "__type__": "BaseState", 
                "session_id": getattr(obj, 'session_id', None)
            }
        
        # fallback to string representation
        return f"<{type(obj).__name__}: {str(obj)}>"