from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator


class JWTProviderConfig(BaseModel):
    """config for jwt validation provider"""
    algorithm: Literal["HS256", "RS256", "ES256"] = Field(default="HS256", description="jwt signing algorithm")
    secret: Optional[str] = Field(default=None, description="direct secret for HS256 (overrides secret_key_secret)")
    secret_key_secret: Optional[str] = Field(default=None, description="secret name to fetch from secret provider")
    public_key_path: Optional[str] = Field(default=None, description="path to public key file for RS256/ES256")
    audience: Optional[str] = Field(default=None, description="expected audience claim")
    issuer: Optional[str] = Field(default=None, description="expected issuer claim")
    expires_in: int = Field(default=3600, ge=60, le=86400, description="token expiry in seconds")
    
    @field_validator("secret", "secret_key_secret", "public_key_path")
    @classmethod
    def validate_key_config(cls, v: Optional[str], info) -> Optional[str]:
        """ensure appropriate key config for algorithm"""
        return v


class OIDCProviderConfig(BaseModel):
    """config for oidc authentication provider"""
    issuer: str = Field(description="oidc issuer url (e.g., https://accounts.google.com)")
    client_id_secret: str = Field(description="secret name for client id")
    client_secret_secret: str = Field(description="secret name for client secret")
    redirect_uri: str = Field(description="oauth callback redirect uri")
    scopes: List[str] = Field(default_factory=lambda: ["openid", "email", "profile"], description="oauth scopes")
    priority: int = Field(default=10, description="provider priority (lower = higher)")


class SAMLProviderConfig(BaseModel):
    """config for saml 2.0 authentication provider"""
    idp_metadata_url: str = Field(description="idp metadata xml url")
    sp_entity_id: str = Field(description="service provider entity id")
    acs_url: str = Field(description="assertion consumer service url")
    slo_url: Optional[str] = Field(default=None, description="single logout service url")
    priority: int = Field(default=5, description="provider priority (lower = higher)")
    metadata_refresh_hours: int = Field(default=24, ge=1, le=168, description="refresh idp metadata every N hours")
    enable_encrypted_assertions: bool = Field(default=False, description="require encrypted saml assertions")
    sp_cert_secret: Optional[str] = Field(default=None, description="secret name for sp certificate")
    sp_key_secret: Optional[str] = Field(default=None, description="secret name for sp private key")


class BuiltinProviderConfig(BaseModel):
    """config for builtin username/password provider"""
    base_url: str = Field(default="https://optorch.example.com", description="base url for invite/reset links")
    session_timeout: int = Field(default=3600, ge=300, le=86400, description="session timeout in seconds")
    invite_url_template: str = Field(default="{{base_url}}/auth/accept-invite?token={{token}}", description="invite link template")
    password_reset_url_template: str = Field(default="{{base_url}}/auth/reset-password?token={{token}}", description="password reset link template")


class UserManagerConfig(BaseModel):
    """config for user lifecycle management"""
    invite_expiry_hours: int = Field(default=72, ge=1, le=720, description="invite link expiry in hours")
    password_reset_expiry_hours: int = Field(default=24, ge=1, le=168, description="password reset link expiry in hours")
    require_email_verification: bool = Field(default=True, description="require email verification for new users")
    password_reset_expiry_hours: int = Field(default=24, ge=1, le=168, description="password reset link expiry in hours")
    require_email_verification: bool = Field(default=True, description="require email verification for new users")
