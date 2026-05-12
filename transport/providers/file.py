import json
import asyncio
import time
from pathlib import Path
from typing import Optional, Dict, Callable
from watchfiles import awatch
from optorch.logging import get_logger
from ..base import BaseTransport, TransportHealthResponse, TransportProbeRequest, TransportProbeResponse, TransportPublishResponse
from ..config import FileTransportConfig

logger = get_logger(__name__)


class FileTransport(BaseTransport):
    """file-based transport using watchfiles for event-driven monitoring"""
    
    def __init__(self, config: FileTransportConfig):
        self.config = config
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._subscriptions: Dict[str, list[Callable]] = {}

    async def check_health(self, request: TransportProbeRequest) -> TransportHealthResponse:
        """touchfile test - create probe, wait for orchestrator response

        Args:
            request: probe request with id, timeout, source

        Returns:
            health status
        """
        try:
            transport_dir = Path(self.config.dir)
            transport_dir.mkdir(parents=True, exist_ok=True)

            probe_file = transport_dir / self.config.probe_template.format(probe_id=request.probe_id)
            response_file = transport_dir / self.config.response_template.format(probe_id=request.probe_id)

            probe_file.write_text(request.model_dump_json())
            logger.debug(f"Wrote probe to {probe_file}")

            start = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start < request.timeout:
                if response_file.exists():
                    response_raw = json.loads(response_file.read_text())
                    response = TransportProbeResponse(**response_raw)
                    probe_file.unlink(missing_ok=True)
                    response_file.unlink(missing_ok=True)
                    
                    return TransportHealthResponse(
                        status="ok",
                        message="Orchestrator responded via file transport",
                        probe_id=response.probe_id,
                        response=response.model_dump()
                    )
                
                await asyncio.sleep(0.1)

            probe_file.unlink(missing_ok=True)
            return TransportHealthResponse(
                status="error",
                error=f"Orchestrator did not respond within {request.timeout}s - check if orchestrator is running and monitoring {self.config.dir}"
            )

        except Exception as e:
            logger.error(f"File transport health check failed: {e}")
            return TransportHealthResponse(
                status="error",
                error=f"File transport error: {str(e)}"
            )
    
    async def start_responder(self) -> bool:
        """start watching for probe files"""
        if not self.config.enabled:
            return False
        
        if self._running:
            logger.warning("File transport responder already running")
            return False
        
        self._running = True
        self._task = asyncio.create_task(self._watch_loop())
        logger.info(f"✅ File transport responder started, watching {self.config.dir}")
        return True
    
    async def stop_responder(self) -> None:
        """stop watching"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("File transport responder stopped")
    
    async def _watch_loop(self) -> None:
        """event-driven watch using watchfiles"""
        transport_dir = Path(self.config.dir)
        transport_dir.mkdir(parents=True, exist_ok=True)
        
        await asyncio.sleep(0.1)
        
        for existing_file in transport_dir.glob("*.queue"):
            if self._running:
                logger.info(f"Processing existing queue file: {existing_file.name}")
                await self._handle_queue_file(existing_file)
        
        async for changes in awatch(transport_dir):
            if not self._running:
                break
                
            for change_type, path in changes:
                path_obj = Path(path)
                
                if path_obj.name.startswith("probe_"):
                    await self._handle_probe(path_obj)
                
                elif path_obj.name.endswith(".queue"):
                    await self._handle_queue_file(path_obj)
    
    async def _handle_queue_file(self, queue_file: Path) -> None:
        """process messages from queue file for subscriptions"""
        try:
            if not queue_file.exists():
                return
            
            channel = queue_file.stem
            
            if channel not in self._subscriptions:
                return
            
            with queue_file.open('r') as f:
                for line in f:
                    if line.strip():
                        message = json.loads(line)
                        for callback in self._subscriptions[channel]:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(message)
                                else:
                                    callback(message)
                            except Exception as e:
                                logger.error(f"Callback error for {channel}: {e}")
            
            queue_file.unlink(missing_ok=True)
            
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Failed to process queue file {queue_file}: {e}")
    
    async def publish(self, channel: str, message: dict) -> TransportPublishResponse:
        """Publish message to channel via JSONL queue file"""
        message["timestamp"] = time.time()
        
        try:
            transport_dir = Path(self.config.dir)
            transport_dir.mkdir(parents=True, exist_ok=True)
            
            queue_file = transport_dir / f"{channel}.queue"
            
            with queue_file.open('a') as f:
                f.write(json.dumps(message) + '\n')
            
            return TransportPublishResponse(status="ok", transport="file", path=str(queue_file))
        except Exception as e:
            logger.error(f"File transport publish failed: {e}")
            return TransportPublishResponse(status="error", transport="file", error=str(e))
    
    async def subscribe(self, channel: str, callback: Callable) -> None:
        """Subscribe to channel - callback invoked on new messages"""
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        
        self._subscriptions[channel].append(callback)
    
    async def unsubscribe(self, channel: str, callback: Callable) -> None:
        """Unsubscribe callback from channel"""
        if channel in self._subscriptions:
            if callback in self._subscriptions[channel]:
                self._subscriptions[channel].remove(callback)
            else:
                logger.debug(f"Callback not found in channel {channel} subscriptions")
    
    async def _handle_probe(self, probe_file: Path) -> None:
        """handle single probe file"""
        try:
            if not probe_file.exists():
                return
            
            probe_raw = json.loads(probe_file.read_text())
            probe = TransportProbeRequest(**probe_raw)
            
            response_file = probe_file.parent / self.config.response_template.format(probe_id=probe.probe_id)
            
            response = TransportProbeResponse(
                probe_id=probe.probe_id,
                status="ok",
                timestamp=asyncio.get_event_loop().time(),
                orchestrator="running"
            )
            
            response_file.write_text(response.model_dump_json())
            logger.debug(f"Responded to probe {probe.probe_id} from {probe.source} via {response_file}")
            
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Failed to handle probe {probe_file}: {e}")
