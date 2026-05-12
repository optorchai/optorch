import json
import asyncio
from typing import Optional
from optorch.logging import get_logger
from ..base import BaseTransport, TransportHealthResponse, TransportProbeRequest, TransportProbeResponse, TransportPublishResponse
from ..config import RedisTransportConfig

logger = get_logger(__name__)


class RedisTransport(BaseTransport):
    """redis pub/sub transport for production setups"""
    
    def __init__(self, config: RedisTransportConfig):
        self.config = config
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def check_health(self, request: TransportProbeRequest) -> TransportHealthResponse:
        """pub/sub probe test - publish to probe channel, wait for response
        
        Args:
            request: probe request with id, timeout, source
            
        Returns:
            health status
        """
        if not self.config or not self.config.connection:
            return TransportHealthResponse(
                status="error",
                error="Redis config not provided"
            )

        try:
            import redis.asyncio as aioredis
        except ImportError:
            return TransportHealthResponse(
                status="error",
                error="redis package not installed - run: pip install redis"
            )

        client = None
        pubsub = None
        
        try:
            client = await aioredis.from_url(
                self.config.connection.url,
                max_connections=self.config.connection.max_connections,
                decode_responses=self.config.connection.decode_responses
            )
            
            await asyncio.to_thread(client.ping)
            
            pubsub = client.pubsub()
            response_channel = f"ui_transport:response:{request.probe_id}"
            await pubsub.subscribe(response_channel)
            
            probe_data = {
                "probe_id": request.probe_id,
                "timestamp": asyncio.get_event_loop().time(),
                "source": request.source,
                "response_channel": response_channel
            }
            probe_channel = self.config.probe_channel
            await client.publish(probe_channel, json.dumps(probe_data))
            logger.debug(f"Published probe to {probe_channel}, waiting on {response_channel}")

            start = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start < request.timeout:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                if message and message['type'] == 'message':
                    response_data = json.loads(message['data'])
                    return TransportHealthResponse(
                        status="ok",
                        message="Orchestrator responded via Redis pub/sub",
                        probe_id=request.probe_id,
                        response=response_data
                    )
                await asyncio.sleep(0.1)

            return TransportHealthResponse(
                status="error",
                error=f"Orchestrator did not respond within {request.timeout}s - check if orchestrator is subscribed to {probe_channel}"
            )

        except Exception as e:
            logger.error(f"Redis transport health check failed: {e}")
            return TransportHealthResponse(
                status="error",
                error=f"Redis transport error: {str(e)}"
            )
    
    async def start_responder(self) -> bool:
        """start redis pub/sub responder"""
        if not self.config.enabled or not self.config.connection:
            return False
        
        if self._running:
            logger.warning("Redis transport responder already running")
            return False
        
        self._running = True
        self._task = asyncio.create_task(self._pubsub_loop())
        logger.info("✅ Redis transport responder started")
        return True
    
    async def stop_responder(self) -> None:
        """stop redis responder"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Redis transport responder stopped")
    
    async def _pubsub_loop(self) -> None:
        """subscribe to probe channel and respond"""
        if not self.config.connection:
            logger.error("Redis connection config not available")
            return
        
        import redis.asyncio as aioredis
        
        client = None
        pubsub = None
        
        try:
            client = await aioredis.from_url(
                self.config.connection.url,
                max_connections=self.config.connection.max_connections,
                decode_responses=self.config.connection.decode_responses
            )
            
            pubsub = client.pubsub()
            await pubsub.subscribe(self.config.probe_channel)
            logger.info(f"Subscribed to {self.config.probe_channel}")
            
            while self._running:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    await self._handle_probe_message(client, message['data'])
                await asyncio.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Redis pubsub loop error: {e}")
        finally:
            if pubsub:
                await pubsub.unsubscribe()
                await pubsub.close()
            if client:
                await client.close()
    
    async def _handle_probe_message(self, client, data: str) -> None:
        """handle probe message and publish response"""
        try:
            probe_raw = json.loads(data)
            probe = TransportProbeRequest(**probe_raw)
            
            response = TransportProbeResponse(
                probe_id=probe.probe_id,
                status="ok",
                timestamp=asyncio.get_event_loop().time(),
                orchestrator="running"
            )
            
            response_channel = f"ui_transport:response:{probe.probe_id}"
            await client.publish(response_channel, response.model_dump_json())
            logger.debug(f"Responded to probe {probe.probe_id} from {probe.source}")
        
        except Exception as e:
            logger.error(f"Failed to handle probe message: {e}")
    
    async def publish(self, channel: str, message: dict) -> TransportPublishResponse:
        """Publish message to Redis pub/sub channel"""
        import json
        import time
        import redis.asyncio as aioredis
        
        message["timestamp"] = time.time()
        
        if not self.config.connection:
            return TransportPublishResponse(status="error", transport="redis", error="connection not configured")
        
        try:
            client = await aioredis.from_url(
                self.config.connection.url,
                max_connections=self.config.connection.max_connections,
                decode_responses=self.config.connection.decode_responses
            )
            await client.publish(channel, json.dumps(message))
            await client.aclose()
            return TransportPublishResponse(status="ok", transport="redis", channel=channel)
        except Exception as e:
            logger.error(f"Redis transport publish failed: {e}")
            return TransportPublishResponse(status="error", transport="redis", error=str(e))
    
    async def subscribe(self, channel: str, callback) -> None:
        """Subscribe to Redis pub/sub channel and invoke callback on messages"""
        import json
        import asyncio
        import redis.asyncio as aioredis
        
        if not self.config.connection:
            logger.error("Redis connection not configured")
            return
        
        connection = self.config.connection
        
        async def listen():
            client = await aioredis.from_url(
                connection.url,
                max_connections=connection.max_connections,
                decode_responses=connection.decode_responses
            )
            pubsub = client.pubsub()
            await pubsub.subscribe(channel)
            
            async for msg in pubsub.listen():
                if msg['type'] == 'message':
                    data = json.loads(msg['data'])
                    callback(data)
        
        asyncio.create_task(listen())
    
    async def unsubscribe(self, channel: str, callback) -> None:
        """Unsubscribe from Redis pub/sub channel"""
        # Redis doesn't support per-callback unsubscribe - connection handles it
        pass
