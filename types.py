"""Optorch type definitions and protocols"""

from typing import Dict, Any, Protocol
from optorch.container import ApplicationContainer

ToolResult = Dict[str, Any]


class AppHooksProtocol(Protocol):
    """Protocol for app-specific hook registration
    
    Hooks are called during orchestrator initialization to register
    app-specific behavior like cleanup handlers and retry logic.
    
    See app/hooks.py for implementation contract.
    """
    
    def __call__(self, container: ApplicationContainer) -> None:
        """Register app hooks with optorch container"""
        ...
