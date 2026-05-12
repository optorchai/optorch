"""errors package config"""
from typing import Literal
from pydantic import BaseModel, Field


class ErrorPolicyConfig(BaseModel):
    """error handling policies"""
    ConfigurationError: Literal["raise", "log", "log_and_raise", "emit", "emit_and_raise"] = "raise"
    ValidationError: Literal["raise", "log", "log_and_raise", "emit", "emit_and_raise"] = "log"
    ProcessorError: Literal["raise", "log", "log_and_raise", "emit", "emit_and_raise"] = "log_and_raise"
    LLMError: Literal["raise", "log", "log_and_raise", "emit", "emit_and_raise"] = "emit_and_raise"
    ToolExecutionError: Literal["raise", "log", "log_and_raise", "emit", "emit_and_raise"] = "emit"
    StateError: Literal["raise", "log", "log_and_raise", "emit", "emit_and_raise"] = "log_and_raise"
    SessionError: Literal["raise", "log", "log_and_raise", "emit", "emit_and_raise"] = "log_and_raise"
    Exception: Literal["raise", "log", "log_and_raise", "emit", "emit_and_raise"] = "log_and_raise"


class ErrorsConfig(BaseModel):
    """error handling configuration"""
    policy: ErrorPolicyConfig = Field(
        default_factory=ErrorPolicyConfig,
        description="Error policies per exception type"
    )
    model_config = {"extra": "allow"}
