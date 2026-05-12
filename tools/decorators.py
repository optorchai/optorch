import inspect
from typing import Any, Callable, get_type_hints, get_origin, get_args
from functools import wraps


def tool(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)
    
    setattr(wrapper, 'name', func.__name__)
    setattr(wrapper, 'get_schema', lambda: _generate_schema(func))
    setattr(wrapper, 'execute', wrapper)
    
    return wrapper


def _generate_schema(func: Callable) -> dict:
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        if param_name in ('self', 'cls'):
            continue
        
        param_type = type_hints.get(param_name, str)
        param_schema = _type_to_schema(param_type)
        
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
        
        properties[param_name] = param_schema
    
    description = func.__doc__.strip() if func.__doc__ else f"Execute {func.__name__}"
    
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }


def _type_to_schema(python_type) -> dict:
    origin = get_origin(python_type)
    
    if origin is list:
        args = get_args(python_type)
        item_type = args[0] if args else str
        return {
            "type": "array",
            "items": _type_to_schema(item_type)
        }
    
    if origin is dict:
        return {"type": "object"}
    
    type_map = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"}
    }
    
    return type_map.get(python_type, {"type": "string"})
