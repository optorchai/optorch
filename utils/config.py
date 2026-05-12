"""config utilities"""
import os
from typing import Optional, overload


@overload
def get_env(name: str) -> Optional[str]: ...

@overload
def get_env(name: str, default: str) -> str: ...

def get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    """simple wrapper for os.getenv - single source for env var access"""
    return os.getenv(name, default)