"""Base MCP Transport Adapter - abstract interface for different MCP protocols"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, TYPE_CHECKING
from optorch.logging import get_logger

if TYPE_CHECKING:
    from ..mcp_config import MCPServerConfig

logger = get_logger(__name__)


class MCPTransportAdapter(ABC):
    """Abstract base class for MCP transport protocols"""
    
    def __init__(self, config: 'MCPServerConfig') -> None:
        self.config = config
        self.url = config.url.rstrip('/')
        self.timeout = config.timeout
        self._connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to MCP server"""
        pass
    
    @abstractmethod
    async def call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        pass
    
    @abstractmethod
    async def list(self) -> List[Dict[str, Any]]:
        """List available tools from MCP server"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the MCP connection"""
        pass
    
    @property
    def is_connected(self) -> bool:
        return self._connected