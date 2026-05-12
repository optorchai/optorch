"""SSE/JSON-RPC Transport Adapter"""
from optorch.logging import get_logger
import json
import asyncio
import time
from typing import Any, Dict, List, TYPE_CHECKING
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import TextContent
from .base import MCPTransportAdapter
from optorch.errors.exceptions import ConfigurationError

if TYPE_CHECKING:
    from ..mcp_config import MCPServerConfig

logger = get_logger(__name__)


class SSEAdapter(MCPTransportAdapter):
    """SSE + JSON-RPC MCP transport (full MCP SDK protocol)
    
    Uses MCP protocol:
    - SSE connection for session management
    - JSON-RPC 2.0 for method calls (tools/list, tools/call)
    - Streaming responses via SSE
    - Auto-reconnection on timeout/disconnection
    - Idle health checks (reconnect if stale >5min)
    """
    
    def __init__(self, config: 'MCPServerConfig') -> None:
        super().__init__(config)
        self._session: ClientSession | None = None
        self._max_retries = 3
        self._retry_delay = 2
        self._connection_task = None
        self._last_call: float = 0
        self._idle_threshold = 300
    
    async def _maintain_connection(self) -> None:
        """Maintain SSE connection in background task with proper context management"""
        try:
            async with sse_client(self.url) as (read, write):
                async with ClientSession(read, write) as session:
                    await asyncio.wait_for(session.initialize(), timeout=self.timeout)
                    self._session = session
                    self._connected = True
                    logger.info(f"✅ SSE MCP connected: {self.url}") 
                    await asyncio.Event().wait()
        except asyncio.CancelledError:
            logger.debug("Connection task cancelled")
            raise
        except asyncio.TimeoutError:
            logger.error(f"MCP initialize timeout after {self.timeout}s: {self.url}")
            raise
        finally:
            self._connected = False
            self._session = None
    
    async def connect(self) -> bool:
        """Establish SSE connection with retry logic"""
        for attempt in range(self._max_retries):
            try:
                logger.debug(f"Connecting to SSE MCP (attempt {attempt + 1}/{self._max_retries}): {self.url}")
                self._connection_task = asyncio.create_task(self._maintain_connection())
                
                for _ in range(50):  # 5 second timeout
                    if self._connected and self._session:
                        return True
                    await asyncio.sleep(0.1)
                
                raise TimeoutError("Connection timeout")
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"SSE connection attempt {attempt + 1}/{self._max_retries} failed: {e}")
                await self._cleanup_connection()
                
                if attempt < self._max_retries - 1:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.debug(f"Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ SSE connection failed after {self._max_retries} attempts: {self.url}")
                    return False
        
        return False
    
    async def _cleanup_connection(self) -> None:
        """Cancel connection task to trigger proper context cleanup"""
        if self._connection_task and not self._connection_task.done():
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
        
        self._connection_task = None
        self._session = None
        self._connected = False
    
    async def call(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call tool via MCP SDK with auto-reconnect on timeout and idle disconnect"""
        if self._session and self._connected:
            idle_time = time.time() - self._last_call
            if idle_time > self._idle_threshold:
                logger.info(f"Session idle for {idle_time:.0f}s (>{self._idle_threshold}s), disconnecting...")
                await self._cleanup_connection()
                self._connected = False
        
        if not self._session or not self._connected:
            logger.debug("Not connected - attempting lazy connection...")
            if not await self.connect():
                raise RuntimeError("Failed to connect to MCP server")
        
        assert self._session is not None, "Session should be initialized after connect()"
        
        self._last_call = time.time()
        
        try:
            result = await asyncio.wait_for(
                self._session.call_tool(tool_name, params),
                timeout=self.timeout
            )
            
            if hasattr(result, 'content') and result.content:
                content = result.content
                if isinstance(content, list) and len(content) > 0:
                    first = content[0]
                    if isinstance(first, TextContent) and hasattr(first, 'text'):
                        try:
                            return json.loads(first.text)
                        except:
                            return {"result": first.text}
            
            return {"result": str(result)}
            
        except Exception as e:
            if 'ClosedResourceError' in str(type(e).__name__):
                logger.warning("Session closed during tool call - reconnecting...")
                await self._cleanup_connection()
                self._connected = False
                if await self.connect():
                    try:
                        logger.info("Reconnected - retrying tool call...")
                        assert self._session is not None
                        self._last_call = time.time()
                        result = await asyncio.wait_for(
                            self._session.call_tool(tool_name, params),
                            timeout=self.timeout
                        )
                        if hasattr(result, 'content') and result.content:
                            content = result.content
                            if isinstance(content, list) and len(content) > 0:
                                first = content[0]
                                if isinstance(first, TextContent) and hasattr(first, 'text'):
                                    try:
                                        return json.loads(first.text)
                                    except:
                                        return {"result": first.text}
                        return {"result": str(result)}
                    except Exception as retry_err:
                        logger.error(f"Retry after reconnect failed: {retry_err}")
                        raise
                raise RuntimeError("Tool call failed - connection lost")
            
            if isinstance(e, asyncio.TimeoutError):
                logger.warning(f"Tool call timeout ({self.timeout}s) - reconnecting...")
                await self._cleanup_connection()
                self._connected = False
                
                if await self.connect():
                    logger.info("Reconnected - retrying tool call...")
                    assert self._session is not None
                    self._last_call = time.time()
                    result = await asyncio.wait_for(
                        self._session.call_tool(tool_name, params),
                        timeout=self.timeout
                    )
                    if hasattr(result, 'content') and result.content:
                        content = result.content
                        if isinstance(content, list) and len(content) > 0:
                            first = content[0]
                            if isinstance(first, TextContent) and hasattr(first, 'text'):
                                try:
                                    return json.loads(first.text)
                                except:
                                    return {"result": first.text}
                    return {"result": str(result)}
                raise RuntimeError("Tool call failed - connection lost")
            
            # http timeouts
            import httpx
            if isinstance(e, (httpx.ReadTimeout, httpx.ConnectTimeout)):
                logger.warning(f"HTTP timeout during tool call - reconnecting...")
                await self._cleanup_connection()
                self._connected = False
                if await self.connect():
                    logger.info("Reconnected after timeout")
                else:
                    logger.error("Failed to reconnect after timeout")
            
            logger.error(f"Tool call failed [{tool_name}]: {e}")
            raise
    
    async def list(self) -> List[Dict[str, Any]]:
        """List tools via MCP SDK with idle disconnect"""
        if self._session and self._connected:
            idle_time = time.time() - self._last_call
            if idle_time > self._idle_threshold:
                logger.info(f"Session idle for {idle_time:.0f}s (>{self._idle_threshold}s), disconnecting...")
                await self._cleanup_connection()
                self._connected = False
        
        if not self._session or not self._connected:
            logger.debug("Not connected - attempting lazy connection...")
            if not await self.connect():
                logger.error("Failed to connect for tool listing")
                return []
        
        assert self._session is not None, "Session should be initialized after connect()"
        
        self._last_call = time.time()
        
        try:
            result = await asyncio.wait_for(self._session.list_tools(), timeout=self.timeout)
            
            tools = []
            if hasattr(result, 'tools'):
                for tool in result.tools:
                    tools.append({
                        "name": tool.name,
                        "description": getattr(tool, 'description', ''),
                        "inputSchema": getattr(tool, 'inputSchema', {})
                    })
            
            return tools
            
        except Exception as e:
            if 'ClosedResourceError' in str(type(e).__name__):
                logger.warning("Session closed - reconnecting...")
                await self._cleanup_connection()
                self._connected = False
                if await self.connect():
                    try:
                        result = await asyncio.wait_for(self._session.list_tools(), timeout=self.timeout)
                        tools = []
                        if hasattr(result, 'tools'):
                            for tool in result.tools:
                                tools.append({
                                    "name": tool.name,
                                    "description": getattr(tool, 'description', ''),
                                    "inputSchema": getattr(tool, 'inputSchema', {})
                                })
                        return tools
                    except Exception as retry_err:
                        logger.error(f"Retry after reconnect failed: {retry_err}")
                        return []
                return []
            
            if isinstance(e, TypeError) and ("'<='" in str(e) or "not supported between instances" in str(e)):
                raise ConfigurationError(
                    f"MCP protocol version mismatch between client and server: {self.url}",
                    details={
                        "error": str(e),
                        "client_sdk": "1.25.0",
                        "url": self.url,
                        "fix": "Upgrade MCP server to @modelcontextprotocol/sdk@^1.25.0 or adjust client SDK version"
                    }
                )
            
            if isinstance(e, asyncio.TimeoutError):
                logger.warning(f"List tools timeout ({self.timeout}s) - reconnecting...")
                await self._cleanup_connection()
                self._connected = False
                return []
            
            import httpx
            if isinstance(e, (httpx.ReadTimeout, httpx.ConnectTimeout)):
                logger.warning(f"HTTP timeout during list - reconnecting...")
                await self._cleanup_connection()
                self._connected = False
            
            logger.error(f"List tools failed: {e}", exc_info=True)
            return []
    
    async def close(self) -> None:
        """Close SSE connection"""
        await self._cleanup_connection()
        self._connected = False
        logger.info(f"SSE MCP disconnected: {self.url}")
    
    def __del__(self):
        """Cleanup on garbage collection - sync fallback"""
        if hasattr(self, '_session') and self._session is not None:
            logger.debug(f"SSE adapter GC cleanup (session will be closed by event loop)")
