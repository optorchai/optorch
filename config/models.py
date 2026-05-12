"""
Pydantic config models for type safety and validation

Provides IDE autocomplete, runtime validation, type checking
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict
from optorch.session.config import SessionConfig
from optorch.lifecycle.config import LifecycleConfig
from optorch.history.config import HistoryConfig
from optorch.cache.config import CacheConfig
from optorch.filters.config import FilterConfig
from optorch.events.config import EventsConfig
from optorch.errors.config import ErrorsConfig
from optorch.llm.config import (
    LLMClientConfig,
    LLMsConfig,
    LLMConfig,
    LLMPoolConfig,
    PromptConfig,
    SuggestionsConfig,
    PromptRegistrationConfig
)


class ReloadConfig(BaseModel):
    """hot-reload configuration"""
    reload_strategy: Literal["ttl", "manual", "always", "none"] = Field(
        default="ttl",
        description="hot-reload strategy - ttl=interval-based, manual=no auto-reload, always=check every access, none=disabled"
    )
    reload_interval: int = Field(
        default=60,
        description="seconds between reload checks (for ttl strategy)",
        ge=1
    )


class ConfigMetadata(BaseModel):
    """Configuration metadata for self-describing config files"""
    directory: Optional[str] = Field(
        default=None,
        description="Directory to load additional YAML configs from"
    )
    files: list[str] = Field(
        default_factory=list,
        description="Additional config files to load and merge - e.g. intents, transformers, tools"
    )


class ExtensionConfig(BaseModel):
    """Base extension config"""
    enabled: bool = Field(
        default=False,
        description="Whether extension is loaded"
    )
    
    model_config = {"extra": "allow"}

class CoreConfig(BaseModel):
    """Root config model - typed, validated, IDE-friendly
    
    Only core optorch components defined here.
    Extensions (budget, evaluation, etc) use extra: allow pattern.
    """
    config: Optional[ReloadConfig] = Field(
        default_factory=ReloadConfig,
        description="config system settings including hot-reload"
    )
    metadata: Optional[ConfigMetadata] = Field(
        default=None,
        description="Config metadata - where to find other config files"
    )
    auto_discover: bool = Field(
        default=True,
        description="Global auto-discovery flag - applies to all packages unless explicitly overridden"
    )
    llm_clients: LLMClientConfig = Field(
        default_factory=LLMClientConfig,
        description="LLM client provider class mappings"
    )
    llms: Optional[LLMsConfig] = Field(
        default=None,
        description="LLM provider configurations"
    )
    llm_pools: Optional[Dict[str, LLMPoolConfig]] = Field(
        default=None,
        description="LLM pools for load balancing across multiple providers"
    )
    llm: Optional[LLMConfig] = Field(
        default=None,
        description="LLM manager configuration"
    )
    prompts: PromptConfig = Field(
        default_factory=PromptConfig,
        description="Prompt system config"
    )
    suggestions: Optional[SuggestionsConfig] = Field(
        default=None,
        description="Follow-up suggestions config"
    )
    prompt_registration: Optional[PromptRegistrationConfig] = Field(
        default=None,
        description="Prompt registration to analytics"
    )
    errors: ErrorsConfig = Field(
        default_factory=ErrorsConfig,
        description="Error handling configuration"
    )
    lifecycle: LifecycleConfig = Field(
        default_factory=LifecycleConfig,
        description="Lifecycle hooks (pre/post dispatch, etc)"
    )
    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="Response caching config"
    )
    history: Optional[HistoryConfig] = Field(
        default=None,
        description="Multi-tier history management"
    )
    session: SessionConfig = Field(
        default_factory=SessionConfig,
        description="Session storage backend"
    )
    events: EventsConfig = Field(
        default_factory=EventsConfig,
        description="Event system configuration"
    )
    filters: FilterConfig = Field(
        default_factory=FilterConfig,
        description="Filter domain/target mappings"
    )
    
    model_config = {"extra": "allow"}