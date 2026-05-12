"""json encoding utilities"""

import json
from decimal import Decimal
from dataclasses import is_dataclass, fields
from typing import Any


def make_json_safe(obj: Any) -> Any:
    """convert any object to JSON-safe representation
    
    shared serialization logic used by:
    - @emits decorator (optorch/events/decorators.py)
    - TimescaleListener (optorch/events/listeners/timescale.py)
    - DecimalEncoder (below)
    """
    if hasattr(obj, '__class__') and obj.__class__.__name__ == 'State':
        return {"type": "State"}
    
    if hasattr(obj, '__class__') and obj.__class__.__name__ == 'LLMResponse':
        return {
            "type": "LLMResponse",
            "usage": obj.usage.to_dict() if hasattr(obj, 'usage') and obj.usage else None
        }
    
    if isinstance(obj, Decimal):
        return float(obj)
    
    if isinstance(obj, list):
        return [make_json_safe(item) for item in obj]
    
    if is_dataclass(obj) and not isinstance(obj, type):
        try:
            return {
                f.name: make_json_safe(getattr(obj, f.name))
                for f in fields(obj)
            }
        except Exception:
            return {"type": type(obj).__name__}
    
    if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict', None)):
        try:
            return obj.to_dict()  # type: ignore
        except Exception:
            return {"type": type(obj).__name__}
    
    if hasattr(obj, '__dict__'):
        return {"type": type(obj).__name__}
    
    return obj


class DecimalEncoder(json.JSONEncoder):
    """json encoder that handles Decimal values, dataclasses, and filters non-serializable objects"""
    
    def default(self, obj):
        result = make_json_safe(obj)
        if result is obj and not isinstance(obj, (str, int, float, bool, type(None))):
            return super().default(obj)
        return result
