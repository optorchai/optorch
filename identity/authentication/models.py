from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC


class Individual(BaseModel):
    """TMF632 Individual - lightweight for authentication (transient)
    
    This is the AUTH Individual - ephemeral, from IDP tokens:
    - Returned by authentication providers (OIDC, SAML, Builtin)
    - Used for JWT claims (subset of fields)
    - No database audit fields (created_at, etc)
    - Lifespan: request duration → converted to JWT → discarded
    
    For PERSISTENCE, see optorch/identity/organization/models.py
    """
    id: str = Field(..., description="Individual ID from IDP (email or UUID)")
    email: Optional[str] = None
    name: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    current_org_id: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    entitlements: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="IDP-specific claims"
    )


class AuthResult(BaseModel):
    """Result of authentication attempt"""
    success: bool
    individual: Optional[Individual] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific response metadata")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific response metadata")


class TokenClaims(BaseModel):
    """JWT token claims"""
    sub: str  # subject (user id)
    email: Optional[str] = None
    name: Optional[str] = None
    org_id: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    entitlements: List[str] = Field(default_factory=list)
    iss: Optional[str] = None  # issuer
    aud: Optional[str] = None  # audience
    exp: Optional[int] = None  # expiration timestamp
    iat: Optional[int] = None  # issued at timestamp
    token_type: Optional[str] = "access"  # "access" or "refresh"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TokenPair(BaseModel):
    """JWT token pair"""
    access_token: str
    expires_in: int
    issued_at: datetime
    refresh_token: Optional[str] = None
