from typing import Protocol, Optional
from optorch.identity.authentication.models import AuthResult


class AuthenticationProvider(Protocol):
    """Authentication provider interface - implement for any IDP"""
    
    async def authenticate(self, request) -> AuthResult:
        """Authenticate request and return individual or error
        
        All individual profile data must be in the returned Individual object.
        Optorch will persist this to its own database.
        
        Args:
            request: HTTP request with auth headers/cookies
        
        Returns:
            AuthResult with individual if valid, error if not
        """
        ...
    
    def priority(self) -> int:
        """Provider priority (for login providers only)
        
        Returns:
            0-100 priority value
            - JWTProvider: N/A (runs alone on protected routes)
            - OIDCProvider: 10 (network call to IDP)
            - SAMLProvider: 15 (XML parsing)
            - BuiltinProvider: 20 (password hashing)
            
        Note: Priority only matters during login provider selection.
        Protected routes ONLY use JWTProvider.
        """
        ...
    
    def name(self) -> str:
        """Provider name for logging/debugging"""
        ...
