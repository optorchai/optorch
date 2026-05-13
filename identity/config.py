"""identity configuration models"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, TYPE_CHECKING
from optorch.storage.config import StorageConfig
from optorch.identity.licensing.usage.config import UsageTrackerConfig
from optorch.identity.provisioning.config import RoleMappingConfig


class LicenseConfig(BaseModel):
    """licensing configuration"""
    mode: Literal["online", "offline", "hybrid"] = Field(
        default="online",
        description="License validation mode"
    )
    online: Dict[str, Any] = Field(
        default_factory=lambda: {
            "validation_url": "https://license.optorch.ai/validate",
            "cache_ttl": 3600
        }
    )
    offline: Dict[str, Any] = Field(
        default_factory=lambda: {
            "public_key_path": "/etc/optorch/license-public.pem"
        }
    )
    usage_tracking: UsageTrackerConfig = Field(
        default_factory=UsageTrackerConfig,
        description="Usage tracking configuration for license enforcement"
    )


class ProvisioningConfig(BaseModel):
    """provisioning configuration"""
    scim_enabled: bool = Field(default=False)
    scim_base_path: str = Field(default="/scim/v2")
    per_tenant_tokens: bool = Field(default=True)
    role_mapping: RoleMappingConfig = Field(
        default_factory=RoleMappingConfig,
        description="Group to role mapping configuration"
    )


class AuthorizationConfig(BaseModel):
    """authorization configuration"""
    provider: Literal["casbin", "opa", "xacml", "memory"] = Field(default="casbin")
    default_decision: Literal["Permit", "Deny"] = Field(default="Deny")
    casbin_model_path: Optional[str] = Field(default=None, description="override path to casbin model.conf; defaults to builtin RBAC model")


class AuthenticationConfig(BaseModel):
    """authentication configuration"""
    jwt: Optional[Any] = Field(
        default_factory=lambda: {
            "algorithm": "HS256",
            "secret_key_secret": "JWT_SECRET",
            "issuer": "optorch",
            "audience": "optorch-api",
            "expires_in": 86400
        },
        description="JWT provider config - enabled by default for OOTB auth"
    )
    builtin: Optional[Any] = Field(
        default_factory=dict,
        description="Builtin provider config - enabled by default for OOTB auth"
    )
    custom_providers: Dict[str, Any] = Field(default_factory=dict)
    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting for authentication requests"
    )


class AuditConfig(BaseModel):
    """audit logging configuration"""
    enable_audit_logging: bool = Field(
        default=True,
        description="Enable audit logging for authentication, authorization, and policy changes"
    )


class WebhookConfig(BaseModel):
    """webhook configuration"""
    enabled: bool = Field(
        default=False,
        description="Enable webhook delivery for identity events"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum delivery retry attempts"
    )
    retry_backoff: float = Field(
        default=1.0,
        description="Retry backoff in seconds (exponential)"
    )
    timeout: float = Field(
        default=10.0,
        description="HTTP timeout for webhook delivery"
    )
    subscriptions: Dict[str, list[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Event subscriptions: {event_type: [{url, headers}]}"
    )


class BootstrapConfig(BaseModel):
    """bootstrap configuration for default org/user creation"""
    create_default_user: bool = Field(default=False)
    default_user: Optional[Dict[str, Any]] = None


class IdentityConfig(BaseModel):
    """identity system configuration"""
    storage: Optional[StorageConfig] = None
    authentication: AuthenticationConfig = Field(default_factory=AuthenticationConfig)
    licensing: LicenseConfig = Field(default_factory=LicenseConfig)
    provisioning: ProvisioningConfig = Field(default_factory=ProvisioningConfig)
    authorization: AuthorizationConfig = Field(default_factory=AuthorizationConfig)
    bootstrap: BootstrapConfig = Field(default_factory=BootstrapConfig)
    audit: AuditConfig = Field(default_factory=AuditConfig)
    webhooks: WebhookConfig = Field(default_factory=WebhookConfig)
