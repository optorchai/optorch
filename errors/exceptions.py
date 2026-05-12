from typing import Optional, Dict


class OptorchError(Exception):
    severity = "medium"
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(OptorchError):
    severity = "critical"


class ValidationError(OptorchError):
    severity = "low"


class ProcessorError(OptorchError):
    def __init__(self, message: str, processor_name: str, phase: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, details)
        self.processor_name = processor_name
        self.phase = phase


class StateError(OptorchError):
    # state management screwup
    pass


class LLMError(OptorchError):
    severity = "high"
    
    def __init__(self, message: str, model: Optional[str] = None, provider: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, details)
        self.model = model
        self.provider = provider


class ToolExecutionError(OptorchError):
    severity = "medium"
    
    def __init__(self, message: str, tool_name: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, details)
        self.tool_name = tool_name


class SessionError(OptorchError):
    severity = "high"
    
    def __init__(self, message: str, session_id: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, details)
        self.session_id = session_id


class BudgetError(OptorchError):
    severity = "medium"
    
    def __init__(self, message: str, scope: Optional[str] = None, exceeded_by: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, details)
        self.scope = scope
        self.exceeded_by = exceeded_by


class NodeContextError(OptorchError):
    severity = "critical"


class HTTPError(OptorchError):
    """HTTP layer errors - route conflicts, middleware issues"""
    severity = "critical"
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict] = None):
        super().__init__(message, details)
        self.status_code = status_code


class AuthenticationError(OptorchError):
    """Authentication failures - invalid credentials, expired tokens"""
    severity = "medium"
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, details)
        self.provider = provider


class AuthorizationError(OptorchError):
    """Authorization denied - insufficient permissions, license limitations"""
    severity = "medium"
    
    def __init__(self, message: str, resource: Optional[str] = None, action: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(message, details)
        self.resource = resource
        self.action = action
