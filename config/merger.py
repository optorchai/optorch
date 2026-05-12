"""
Deep merge utilities for config fallback chain

Handles special markers:
- __replace__: true → replace entire section
- key: null → delete key from result
"""
from typing import Any
from copy import deepcopy


def deep_get(data: dict, key_path: str, default: Any = None) -> Any:
    """
    Get nested dict value by dot-separated path
    
    Examples:
        deep_get({"a": {"b": 1}}, "a.b") → 1
        deep_get({"a": {"b": 1}}, "a.c", 99) → 99
    """
    keys = key_path.split(".")
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def deep_set(data: dict, key_path: str, value: Any) -> None:
    """
    Set nested dict value by dot-separated path
    
    Examples:
        deep_set({}, "a.b.c", 42) → {"a": {"b": {"c": 42}}}
    """
    keys = key_path.split(".")
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


def deep_merge(base: dict, override: dict) -> dict:
    """
    Deep merge with special marker support
    
    Special markers:
        __replace__: true → replace entire section
        key: null → delete key from result
    
    Examples:
        deep_merge({"a": 1, "b": 2}, {"b": 3, "c": 4})
        → {"a": 1, "b": 3, "c": 4}
        
        deep_merge({"a": {"x": 1}}, {"a": {"__replace__": true, "y": 2}})
        → {"a": {"y": 2}}
        
        deep_merge({"a": 1, "b": 2}, {"b": null})
        → {"a": 1}
    """
    result = deepcopy(base)
    
    for key, value in override.items():
        # null deletes key
        if value is None:
            result.pop(key, None)
            continue
        
        # __replace__ marker discards base value
        if isinstance(value, dict) and value.get("__replace__"):
            clean_value = {k: v for k, v in value.items() if k != "__replace__"}
            result[key] = clean_value
            continue
        
        # recursive merge for dicts
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    
    return result
