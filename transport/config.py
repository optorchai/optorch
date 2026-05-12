"""transport configuration models"""
from pydantic import BaseModel, Field
from typing import Optional
from optorch.session.storage.config import RedisConfig


class TransportProviderConfig(BaseModel):
    """base config for transport providers"""
    enabled: bool = Field(default=False, description="enable this provider")    
    public_fields: list[str] = Field(default=["enabled"], exclude=True)


class FileTransportConfig(TransportProviderConfig):
    """file transport provider config"""
    enabled: bool = Field(default=True, description="enable this provider")
    dir: str = Field(default="/tmp/optorch/transport", description="transport directory")
    probe_template: str = Field(default="probe_{probe_id}.json", description="probe file naming template")
    response_template: str = Field(default="response_{probe_id}.json", description="response file naming template")
    public_fields: list[str] = Field(default=["enabled", "dir"], exclude=True)


class RedisTransportConfig(TransportProviderConfig):
    """redis transport provider config - reuses storage.redis connection"""
    connection: Optional[RedisConfig] = Field(default=None, description="redis connection config - injected from storage.redis if not provided")
    probe_channel: str = Field(default="optorch:transport:probe", description="redis channel for probe messages")
    response_channel: str = Field(default="optorch:transport:response", description="redis channel for response messages")
    key_prefix: str = Field(default="optorch:transport:", description="redis key prefix for transport data")
    public_fields: list[str] = Field(default=["enabled", "connection"], exclude=True)


class KafkaTransportConfig(TransportProviderConfig):
    """kafka transport provider config - extends enterprise KafkaConfig with optional overrides"""
    # optional overrides from enterprise.kafka master config
    bootstrap_servers: Optional[str] = Field(default=None, description="override kafka bootstrap servers from enterprise.kafka")
    topic: Optional[str] = Field(default=None, description="override kafka topic from enterprise.kafka")
    group_id: Optional[str] = Field(default=None, description="override kafka group_id from enterprise.kafka")
    
    # transport-specific fields
    probe_topic: str = Field(default="optorch-transport-probe", description="kafka topic for probe messages")
    response_topic: str = Field(default="optorch-transport-response", description="kafka topic for response messages")
    consumer_group: str = Field(default="optorch-transport-ui", description="kafka consumer group id for transport")
    public_fields: list[str] = Field(default=["enabled", "bootstrap_servers"], exclude=True)


class TransportConfig(BaseModel):
    """ui transport configuration - reuses existing redis/kafka configs"""
    
    active_provider: Optional[str] = Field(
        default=None,
        description="Currently selected transport (kafka/redis/file). If None, uses first enabled."
    )
    
    file: FileTransportConfig = Field(default_factory=FileTransportConfig)
    redis: RedisTransportConfig = Field(default_factory=RedisTransportConfig)
    kafka: KafkaTransportConfig = Field(default_factory=KafkaTransportConfig)
