"""decimal conversion utilities"""

from decimal import Decimal, InvalidOperation
from typing import Any


def safe_decimal(value: Any, default: str = "0") -> Decimal:
    """convert any value to Decimal safely
    
    handles: None, empty dict, strings, floats, ints, existing Decimals
    falls back to default on any conversion error
    """
    if isinstance(value, Decimal):
        return value
    
    if value is None or value == {} or value == "":
        return Decimal(default)
    
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        return Decimal(default)
