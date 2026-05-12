"""llm package configuration models"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from optorch.config.path_config import PathConfig
    from optorch.session.storage import RedisConfig, QdrantConfig


class LLMProviderConfig(BaseModel):
    """single llm configuration"""
    provider: str = Field(
        description="LLM provider type (openai, groq, anthropic, ollama, or custom)"
    )
    model: str = Field(description="Model identifier (e.g. gpt-4, llama3)")
    type: Optional[str] = Field(
        default="client",
        description="Type: 'client' for single instance, 'pool' for multiple API keys (legacy pattern)"
    )
    key_prefix: Optional[str] = Field(
        default=None,
        description="Secret reference name - e.g. OPENAI_API_KEY. For pools, looks for _2, _3, etc."
    )
    temperature: float = Field(
        ge=0, le=2, default=0.7,
        description="Sampling temperature - higher = more random"
    )
    strategy: Optional[str] = Field(
        default="round_robin",
        description="Pool load balancing strategy (round_robin, least_busy, weighted) - only used when type=pool"
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Max tokens in response - None = model default"
    )
    timeout: int = Field(default=30, description="Request timeout seconds")
    base_url: Optional[str] = Field(
        default=None,
        description="Custom API endpoint (Ollama local, Azure, etc)"
    )
    top_p: Optional[float] = Field(
        default=None, ge=0, le=1,
        description="Nucleus sampling - alternative to temperature"
    )
    frequency_penalty: Optional[float] = Field(
        default=None, ge=-2, le=2,
        description="Penalize token frequency - reduce repetition"
    )
    presence_penalty: Optional[float] = Field(
        default=None, ge=-2, le=2,
        description="Penalize token presence - encourage new topics"
    )
    stop: Optional[List[str]] = Field(
        default=None,
        description="Stop sequences - end generation early"
    )
    streaming: bool = Field(
        default=False,
        description="Enable streaming responses"
    )
    completion_type: str = Field(
        default="hard_stop",
        description="How streaming buffers chunks when budget exceeded (hard_stop, sentence, paragraph, min_tokens)"
    )
    
    model_config = {"extra": "allow"}


class LLMPoolConfig(BaseModel):
    """llm pool configuration for load balancing"""
    clients: List[str] = Field(
        description="List of LLM profile names to include in pool (e.g., ['default', 'fast'])"
    )
    strategy: str = Field(
        default="round_robin",
        description="Load balancing strategy (round_robin, least_busy, weighted)"
    )
    fallback: bool = Field(
        default=True,
        description="Enable fallback to next client on failure"
    )
    max_retries: int = Field(
        default=1,
        description="Max retry attempts per client before fallback (0 = no retries, just fallback)"
    )
    retry_delay: float = Field(
        default=1.0,
        description="Delay in seconds between retry attempts"
    )
    timeout: Optional[float] = Field(
        default=None,
        description="Request timeout in seconds (None = no timeout)"
    )
    circuit_breaker_threshold: int = Field(
        default=5,
        description="Failures before marking client unhealthy (0 = disabled)"
    )
    circuit_breaker_timeout: int = Field(
        default=60,
        description="Seconds before retrying unhealthy client"
    )
    
    model_config = {"extra": "allow"}


class LLMClientConfig(BaseModel):
    """llm client provider class mappings"""
    providers: Dict[str, str] = Field(
        default_factory=lambda: {
            "openai": "OpenAIClient",
            "groq": "GroqClient",
            "ollama": "OllamaClient",
        },
        description="Provider name to client class mappings"
    )
    module: str = Field(
        default="optorch.llm.clients",
        description="Module containing client classes"
    )
    
    model_config = {"extra": "allow"}


class LLMsConfig(BaseModel):
    """llm configurations - default + custom"""
    default: LLMProviderConfig = Field(
        description="Default LLM for all operations"
    )
    fast: Optional[LLMProviderConfig] = Field(
        default=None,
        description="Fast/cheap LLM for suggestions, simple tasks"
    )
    
    model_config = {"extra": "allow"}


class LLMConfig(BaseModel):
    """llm manager configuration"""
    default_provider: Optional[str] = None
    timeout: int = Field(default=30)
    max_retries: int = Field(default=3)
    params: Dict[str, Any] = Field(default_factory=dict)
    auto_discover: bool | None = Field(default=None, description="enable transformer auto-discovery")
    transformers: Optional["PathConfig"] = Field(
        default=None,
        description="transformer discovery config"
    )
    lifecycle: Optional[Dict[str, Any]] = Field(
        default=None,
        description="lifecycle processor configuration"
    )
    
    def __init__(self, **data):
        if "transformers" not in data or data["transformers"] is None:
            from optorch.config.path_config import PathConfig
            data["transformers"] = PathConfig(module="app.transformers", auto_discover=True, instantiate=False)
        super().__init__(**data)


class PromptConfig(BaseModel):
    """prompt manager configuration"""
    directory: str = Field(default="prompts")
    fragments: Dict[str, str] = Field(default_factory=dict)    
    inline_prompts: Optional[Dict[str, str]] = Field(default=None, description="Inline prompt dict")
    loader_callable: Optional[Any] = Field(default=None, description="Dynamic prompt loader function")
    auto_discover: bool = Field(default=False, description="Auto-discover custom PromptProvider classes")
    providers_modules: List[str] = Field(
        default_factory=lambda: [
            "app.prompts.providers",
            "app.prompts",
            "prompts.providers",
            "prompts"
        ],
        description="Modules to search for custom providers (tries in order, stops at first success)"
    )
    redis: Optional["RedisConfig"] = Field(
        default=None,
        description="redis connection config for prompt caching"
    )
    qdrant: Optional["QdrantConfig"] = Field(
        default=None,
        description="qdrant connection config for prompt storage"
    )


class SuggestionsConfig(BaseModel):
    """suggestions feature config"""
    enabled: bool = Field(
        default=True,
        description="Enable follow-up suggestions after responses"
    )
    count: int = Field(
        ge=1, le=10, default=3,
        description="Number of suggestions to generate"
    )
    llm: str = Field(
        default="fast",
        description="Which LLM to use (key from llms config)"
    )


class PromptRegistrationConfig(BaseModel):
    """prompt registration to analytics"""
    enabled: bool = Field(
        default=True,
        description="Enable prompt registration"
    )
    auto_register: bool = Field(
        default=True,
        description="Auto-register prompts to Analytics on first LLM call"
    )
    version_strategy: str = Field(
        default="hash",
        description="Version strategy (hash, timestamp, manual)"
    )
    analytics_url: str = Field(
        default="http://localhost:8001/v1",
        description="Analytics API base URL"
    )


# rebuild models to resolve forward references from TYPE_CHECKING
def _rebuild_models():
    """resolve forward references after imports available"""
    try:
        from optorch.config.path_config import PathConfig
        from optorch.session.storage import RedisConfig, QdrantConfig
        
        LLMConfig.model_rebuild()
        PromptConfig.model_rebuild()
    except ImportError:
        pass  # optional dependencies not installed

_rebuild_models()
