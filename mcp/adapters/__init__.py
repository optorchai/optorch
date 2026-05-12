"""MCP Transport Adapters"""
from typing import Dict, Type
from .base import MCPTransportAdapter
from .http_adapter import HTTPAdapter
from .sse_adapter import SSEAdapter


class AdapterRegistry:
    """registry for MCP transport adapters"""
    
    _adapters: Dict[str, Type[MCPTransportAdapter]] = {}
    
    @classmethod
    def register(cls, transport: str, adapter_class: Type[MCPTransportAdapter]) -> None:
        """register transport adapter"""
        cls._adapters[transport] = adapter_class
    
    @classmethod
    def get(cls, transport: str) -> Type[MCPTransportAdapter]:
        """get adapter class for transport type"""
        adapter = cls._adapters.get(transport)
        if not adapter:
            raise ValueError(f"Unknown transport type: {transport}")
        return adapter


# auto-register built-in adapters
AdapterRegistry.register('http', HTTPAdapter)
AdapterRegistry.register('sse', SSEAdapter)

__all__ = ['MCPTransportAdapter', 'HTTPAdapter', 'SSEAdapter', 'AdapterRegistry']