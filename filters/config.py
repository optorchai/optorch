"""filters package config"""
from typing import Dict, List
from pydantic import BaseModel, Field
from optorch.config.path_config import PathConfig


class FilterConfig(BaseModel):
    """filter domain/target mappings"""
    auto_discover: bool | None = Field(default=None, description="enable custom filter discovery")
    filters_path: PathConfig = Field(
        default_factory=lambda: PathConfig(module="app.filters", auto_discover=True, instantiate=False),
        description="custom filters discovery config"
    )
    domains: Dict[str, Dict[str, List[str]]] = Field(
        default_factory=lambda: {
            "messages": {
                "groq": ["normalize_format", "unsupported_fields"],
                "openai": ["normalize_format", "unsupported_fields"],
                "ollama": ["normalize_format", "unsupported_fields"],
            },
            "events": {
                "audit": ["add_session_context", "remove_pii"],
                "development": ["add_session_context", "debug_info"],
                "production": ["add_session_context", "remove_pii"],
                "interaction": ["add_session_context"],
                "message": ["add_session_context"],
                "error": ["add_session_context"],
                "llm": ["add_session_context"],
            },
            "tools": {
                "input": ["validate_tool_params"],
                "output": ["sanitize_tool_output"],
            },
            "state": {
                "persist": ["redact_sensitive_state", "compact_state"],
            },
        },
        description="filter mappings per domain/target"
    )
    
    model_config = {"extra": "allow"}
