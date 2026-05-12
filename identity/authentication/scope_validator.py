"""JWT scope validation middleware"""

from typing import List, Optional, Set
from optorch.errors import AuthorizationError
from optorch.logging import get_logger

logger = get_logger(__name__)


class ScopeValidator:
    """validates JWT scopes against required permissions"""
    
    def __init__(self, scope_mapping: Optional[dict] = None):
        """
        Args:
            scope_mapping: maps scopes to granular permissions
                Example: {"read:users": ["user.read", "user.list"]}
        """
        self.scope_mapping = scope_mapping or self._default_mapping()
    
    def validate(self, token_scopes: List[str], required_scopes: List[str]) -> bool:
        """check if token has required scopes
        
        Args:
            token_scopes: scopes from JWT claims
            required_scopes: scopes required for operation
            
        Returns:
            True if authorized
            
        Raises:
            AuthorizationError: Missing required scopes
        """
        token_scope_set = set(token_scopes)
        required_scope_set = set(required_scopes)
        expanded_token = self._expand_scopes(token_scope_set)
        expanded_required = self._expand_scopes(required_scope_set)
        
        missing = expanded_required - expanded_token
        
        if missing:
            raise AuthorizationError(
                f"Insufficient scopes",
                details={
                    "required": list(required_scopes),
                    "missing": list(missing),
                    "token_scopes": token_scopes
                }
            )
        
        logger.debug(f"Scope validation passed: {required_scopes}")
        return True
    
    def _expand_scopes(self, scopes: Set[str]) -> Set[str]:
        """expand scopes using mapping"""
        expanded = set(scopes)
        
        for scope in scopes:
            if scope in self.scope_mapping:
                expanded.update(self.scope_mapping[scope])
        
        return expanded
    
    def _default_mapping(self) -> dict:
        """default scope mappings"""
        return {
            "read:users": ["user.read", "user.list"],
            "write:users": ["user.create", "user.update", "user.delete"],
            "read:teams": ["team.read", "team.list"],
            "write:teams": ["team.create", "team.update", "team.delete"],
            "admin": ["*"],
            "urn:ietf:params:scim:schemas:core:2.0:User": ["user.read", "user.write"],
            "urn:ietf:params:scim:schemas:core:2.0:Group": ["team.read", "team.write"],
        }
    
    def require_scopes(self, *scopes: str):
        """decorator for scope enforcement"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                token_scopes = kwargs.get("token_scopes", [])
                self.validate(token_scopes, list(scopes))
                return await func(*args, **kwargs)
            return wrapper
        return decorator
