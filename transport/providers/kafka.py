import json
import asyncio
from typing import Optional
from optorch.logging import get_logger
from ..base import BaseTransport, TransportHealthResponse, TransportProbeRequest, TransportProbeResponse, TransportPublishResponse
from ..config import KafkaTransportConfig

logger = get_logger(__name__)


class KafkaTransport(BaseTransport):
    """kafka topic transport for enterprise setups"""
    
    def __init__(self, config: KafkaTransportConfig):
        self.config = config
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def check_health(self, request: TransportProbeRequest) -> TransportHealthResponse:
        """kafka probe test - produce to probe topic, consume from response topic
        
        Args:
            request: probe request with id, timeout, source
            
        Returns:
            health status
        """
        if not self.config or not self.config.bootstrap_servers:
            return TransportHealthResponse(
                status="error",
                error="Kafka config not provided"
            )

        try:
            from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
        except ImportError:
            return TransportHealthResponse(
                status="error",
                error="aiokafka package not installed - run: pip install aiokafka"
            )

        producer = None
        consumer = None
        
        try:
            response_topic = f"ui_transport_response_{request.probe_id}"
            consumer = AIOKafkaConsumer(
                response_topic,
                bootstrap_servers=self.config.bootstrap_servers,
                auto_offset_reset='earliest',
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            await consumer.start()
            logger.debug(f"Kafka consumer started on {response_topic}")

            producer = AIOKafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await producer.start()
            
            probe_data = {
                "probe_id": request.probe_id,
                "timestamp": asyncio.get_event_loop().time(),
                "source": request.source,
                "response_topic": response_topic
            }
            probe_topic = self.config.probe_topic
            await producer.send_and_wait(probe_topic, probe_data)
            logger.debug(f"Sent probe to {probe_topic}")

            start = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start < request.timeout:
                msg_batch = await consumer.getmany(timeout_ms=100)
                for tp, messages in msg_batch.items():
                    for message in messages:
                        response_data = message.value
                        return TransportHealthResponse(
                            status="ok",
                            message="Orchestrator responded via Kafka topic",
                            probe_id=request.probe_id,
                            response=response_data
                        )
                await asyncio.sleep(0.1)

            return TransportHealthResponse(
                status="error",
                error=f"Orchestrator did not respond within {request.timeout}s - check if orchestrator is consuming from {probe_topic}"
            )

        except Exception as e:
            logger.error(f"Kafka transport health check failed: {e}")
            return TransportHealthResponse(
                status="error",
                error=f"Kafka transport error: {str(e)}"
            )
    
    async def start_responder(self) -> bool:
        """start kafka consumer responder"""
        if not self.config.enabled or not self.config.bootstrap_servers:
            return False
        
        if self._running:
            logger.warning("Kafka transport responder already running")
            return False
        
        self._running = True
        self._task = asyncio.create_task(self._consumer_loop())
        logger.info("✅ Kafka transport responder started")
        return True
    
    async def stop_responder(self) -> None:
        """stop kafka responder"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Kafka transport responder stopped")
    
    async def _consumer_loop(self) -> None:
        """consume probe topic and produce responses"""
        if not self.config.bootstrap_servers:
            logger.error("Kafka bootstrap_servers not configured")
            return
        
        from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
        
        consumer = None
        producer = None
        
        try:
            consumer = AIOKafkaConsumer(
                self.config.probe_topic,
                bootstrap_servers=self.config.bootstrap_servers,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            await consumer.start()
            
            producer = AIOKafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await producer.start()
            
            logger.info(f"Consuming from {self.config.probe_topic}")
            
            async for message in consumer:
                if not self._running:
                    break
                if message.value:
                    await self._handle_probe_message(producer, message.value)
        
        except Exception as e:
            logger.error(f"Kafka consumer loop error: {e}")
        finally:
            if consumer:
                await consumer.stop()
            if producer:
                await producer.stop()
    
    async def _handle_probe_message(self, producer, probe_raw: dict) -> None:
        """handle probe message and produce response"""
        try:
            probe = TransportProbeRequest(**probe_raw)
            
            response = TransportProbeResponse(
                probe_id=probe.probe_id,
                status="ok",
                timestamp=asyncio.get_event_loop().time(),
                orchestrator="running"
            )
            
            response_topic = f"ui_transport_response_{probe.probe_id}"
            await producer.send_and_wait(response_topic, response.model_dump())
            logger.debug(f"Responded to probe {probe.probe_id} from {probe.source}")
        
        except Exception as e:
            logger.error(f"Failed to handle probe message: {e}")
    
    async def publish(self, channel: str, message: dict) -> TransportPublishResponse:
        """Publish message to Kafka topic"""
        import json
        import time
        from aiokafka import AIOKafkaProducer
        
        message["timestamp"] = time.time()
        
        if not self.config.bootstrap_servers:
            return TransportPublishResponse(status="error", transport="kafka", error="bootstrap_servers not configured")
        
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            await producer.start()
            try:
                await producer.send(channel, message)
                return TransportPublishResponse(status="ok", transport="kafka", topic=channel)
            finally:
                await producer.stop()
        except Exception as e:
            logger.error(f"Kafka transport publish failed: {e}")
            return TransportPublishResponse(status="error", transport="kafka", error=str(e))
            await producer.send_and_wait(channel, value=message)
        finally:
            await producer.stop()
    
    async def subscribe(self, channel: str, callback) -> None:
        """Subscribe to Kafka topic and invoke callback on messages"""
        import json
        import asyncio
        from aiokafka import AIOKafkaConsumer
        
        if not self.config.bootstrap_servers:
            logger.error("Kafka bootstrap_servers not configured")
            return
        
        bootstrap_servers = self.config.bootstrap_servers
        
        async def consume():
            consumer = AIOKafkaConsumer(
                channel,
                bootstrap_servers=bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id=self.config.consumer_group,
                auto_offset_reset='earliest'
            )
            await consumer.start()
            try:
                async for msg in consumer:
                    callback(msg.value)
            finally:
                await consumer.stop()
        
        asyncio.create_task(consume())
    
    async def unsubscribe(self, channel: str, callback) -> None:
        """Unsubscribe from Kafka topic"""
        # Kafka doesn't support per-callback unsubscribe - consumer group handles it
        pass
