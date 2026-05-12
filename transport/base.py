from abc import ABC, abstractmethod
from typing import Dict, Any, Callable
from pydantic import BaseModel, Field


class TransportProbeRequest(BaseModel):
    """probe request for transport health checks"""
    probe_id: str = Field(description="unique probe identifier")
    timeout: float = Field(default=5.0, description="max wait time in seconds")
    source: str = Field(default="unknown", description="identifier of the source making the probe")


class TransportProbeResponse(BaseModel):
    """probe response from orchestrator"""
    probe_id: str = Field(description="probe identifier from request")
    status: str = Field(description="orchestrator status")
    timestamp: float = Field(description="response timestamp")
    orchestrator: str = Field(default="running", description="orchestrator state")


class TransportHealthResponse(BaseModel):
    """standard response for transport health checks"""
    status: str  # 'ok' or 'error'
    message: str | None = None
    error: str | None = None
    probe_id: str | None = None
    response: Dict[str, Any] | None = None


class TransportPublishResponse(BaseModel):
    """response from transport publish operation"""
    status: str  # 'ok' or 'error'
    transport: str  # 'kafka', 'redis', 'file'
    error: str | None = None
    channel: str | None = None
    topic: str | None = None
    path: str | None = None


class BaseTransport(ABC):
    """base class for UI transport health checks"""
    
    @abstractmethod
    def __init__(self, config: Any) -> None:
        """initialize transport with config"""
        pass
    
    @abstractmethod
    async def publish(self, channel: str, data: Dict[str, Any]) -> 'TransportPublishResponse':
        """publish event to transport channel - returns ack"""
        pass
    
    @abstractmethod
    async def subscribe(self, channel: str, callback: Callable) -> None:
        """subscribe to transport channel"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, channel: str, callback: Callable) -> None:
        """unsubscribe from transport channel"""
        pass
    
    @abstractmethod
    async def check_health(self, request: TransportProbeRequest) -> TransportHealthResponse:
        """check transport health via probe test
        
        Args:
            request: probe request with probe_id, timeout, source
            
        Returns:
            standardized health response
        """
        pass
    
    @abstractmethod
    async def start_responder(self) -> bool:
        """start transport responder for health checks
        
        Returns:
            True if started, False if already running or disabled
        """
        pass
    
    @abstractmethod
    async def stop_responder(self) -> None:
        """stop transport responder"""
        pass
