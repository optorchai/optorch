"""Multi-tenant context tracking

Provides session-local storage for tracking:
- application_id: Which app/service is running (pricing-engine, quote-builder, etc)
- user_id: End user making requests
- client_id: Customer/organization (B2B multi-tenancy)
- request_id: Unique request identifier for tracing

Used by event emission to auto-populate tenant fields.

Usage:
    from optorch.tenant_context import TenantContext
    
    # Set context (e.g., from API middleware)
    TenantContext.set(
        application_id="pricing-engine",
        user_id="user@example.com",
        client_id="acme-corp"
    )
    
    # Events auto-include tenant context
    emitter.emit("llm.start", {...})  # includes application_id, user_id, client_id
    
    # Get current context
    ctx = TenantContext.get()
    
    # Clear context (end of request)
    TenantContext.clear()
"""
from contextvars import ContextVar
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
import uuid


class TenantContextData(BaseModel):
    """Multi-tenant context data"""
    model_config = ConfigDict(extra='forbid')
    application_id: str = "orchestrator"
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict excluding None values"""
        return {k: v for k, v in self.model_dump().items() if v is not None}

_tenant_context: ContextVar[Optional[TenantContextData]] = ContextVar('tenant_context', default=None)


class TenantContext:
    """global accessor for tenant context"""
    
    @staticmethod
    def set(
        application_id: str,
        user_id: Optional[str] = None,
        client_id: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> None:
        """set tenant context for current execution"""
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        ctx = TenantContextData(
            application_id=application_id,
            user_id=user_id,
            client_id=client_id,
            request_id=request_id,
            session_id=session_id
        )
        _tenant_context.set(ctx)
    
    @staticmethod
    def get() -> TenantContextData:
        """get current tenant context"""
        ctx = _tenant_context.get()
        return ctx if ctx else TenantContextData()
    
    @staticmethod
    def get_dict() -> Dict[str, Any]:
        """get context as dict (empty if not set)"""
        ctx = _tenant_context.get()
        return ctx.to_dict() if ctx else {}
    
    @staticmethod
    def clear() -> None:
        """clear tenant context"""
        _tenant_context.set(None)
    
    @staticmethod
    def get_application_id() -> Optional[str]:
        """get just application_id"""
        ctx = _tenant_context.get()
        return ctx.application_id if ctx else None
    
    @staticmethod
    def get_user_id() -> Optional[str]:
        """get just user_id"""
        ctx = _tenant_context.get()
        return ctx.user_id if ctx else None
    
    @staticmethod
    def get_client_id() -> Optional[str]:
        """get just client_id"""
        ctx = _tenant_context.get()
        return ctx.client_id if ctx else None
    
    @staticmethod
    def get_request_id() -> Optional[str]:
        """get just request_id"""
        ctx = _tenant_context.get()
        return ctx.request_id if ctx else None
    
    @staticmethod
    def get_session_id() -> Optional[str]:
        """get just session_id"""
        ctx = _tenant_context.get()
        return ctx.session_id if ctx else None
