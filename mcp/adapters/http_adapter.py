"""HTTP Transport Adapter - simplified REST-based MCP protocol"""
import httpx
from optorch.logging import get_logger
from typing import Any, Dict, List, TYPE_CHECKING
from .base import MCPTransportAdapter
from optorch.utils import sanitize_path

if TYPE_CHECKING:
    from ..mcp_config import MCPServerConfig

logger = get_logger(__name__)


class HTTPAdapter(MCPTransportAdapter):
    """HTTP-based MCP transport (simplified protocol)"""
    
    def __init__(self, config: 'MCPServerConfig') -> None:
        super().__init__(config)
        self.client = httpx.AsyncClient(timeout=int(self.timeout))
        self.call_endpoint = self.config.http_call_endpoint
        self.list_endpoint = self.config.http_list_endpoint
    
    async def connect(self) -> bool:
        """Mark as connected - HTTP doesn't need explicit connection"""
        self._connected = True
        logger.info(f"HTTP MCP ready: {self.url}")
        return True
    
    async def call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via HTTP POST"""
        if not self._connected:
            await self.connect()
        
        try:
            response = await self.client.post(
                sanitize_path(self.url, self.call_endpoint),
                json={"tool": tool_name, "params": params}
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"HTTP tool call failed [{tool_name}]: {response.status_code}")
            return {"error": f"Tool call failed: {response.status_code}"}
        except Exception as e:
            logger.error(f"HTTP tool call error [{tool_name}]: {e}")
            return {"error": str(e)}
    
    async def list(self) -> List[Dict[str, Any]]:
        """List tools via HTTP GET"""
        try:
            response = await self.client.get(sanitize_path(self.url, self.list_endpoint))
            if response.status_code == 200:
                data = response.json()
                tools = data.get("tools", [])
                return [{"name": t} if isinstance(t, str) else t for t in tools]
            
            logger.error(f"HTTP list failed: {response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Failed to list HTTP MCP tools: {e}")
            return []
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
        self._connected = False