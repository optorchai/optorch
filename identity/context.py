"""identity context - ambient current user/org state via contextvars

request-scoped isolation for multi-tenant data access
contextvars provide async-safe, thread-safe per-request context
"""

from typing import Optional
from contextvars import ContextVar


# request-scoped context vars - yuk, but hey, this is exactly what context vars are for
_current_user: ContextVar[Optional[dict]] = ContextVar('current_user', default=None)
_current_org_id: ContextVar[Optional[str]] = ContextVar('current_org_id', default=None)


class IdentityContext:
    """manages ambient identity context using contextvars for request isolation
    
    each HTTP request gets isolated context automatically
    no cross-request contamination in async/multi-threaded environments
    """

    def set_current_user(self, user: dict) -> None:
        """set current user in request-scoped context"""
        _current_user.set(user)
        if "current_org_id" in user:
            _current_org_id.set(user["current_org_id"])

    def get_current_user(self) -> Optional[dict]:
        """get current user from request-scoped context"""
        return _current_user.get()

    def get_current_org_id(self) -> Optional[str]:
        """get current org id from request-scoped context"""
        return _current_org_id.get()
    
    def set_current_org(self, org_id: str) -> None:
        """set current org id in request-scoped context"""
        _current_org_id.set(org_id)

    def clear(self) -> None:
        """clear request-scoped context"""
        _current_user.set(None)
        _current_org_id.set(None)
    
    @staticmethod
    def get_ambient_org_id() -> Optional[str]:
        """get ambient org_id from contextvars without instance
        
        allows storage layer to read context without IdentityContext instance
        """
        return _current_org_id.get()
