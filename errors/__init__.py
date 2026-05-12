# unified error handling
from optorch.errors.handler import ErrorHandler, ErrorContext, ErrorAction
from optorch.errors.decorators import error_context
from optorch.errors.exceptions import (
    OptorchError,
    ConfigurationError,
    ValidationError,
    ProcessorError,
    StateError,
    LLMError,
    ToolExecutionError,
    SessionError,
    BudgetError,
    HTTPError,
    AuthenticationError,
    AuthorizationError,
)

__all__ = [
    "ErrorHandler",
    "ErrorContext",
    "ErrorAction",
    "error_context",
    "OptorchError",
    "ConfigurationError",
    "ValidationError",
    "ProcessorError",
    "StateError",
    "LLMError",
    "ToolExecutionError",
    "SessionError",
    "BudgetError",
    "HTTPError",
    "AuthenticationError",
    "AuthorizationError",
]
