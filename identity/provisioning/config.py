"""SCIM provisioning configuration"""

from pydantic import BaseModel, Field


class RoleMappingConfig(BaseModel):
    """Configure SCIM group to role mapping
    
    SCIM doesnt define group-to-role mappings - each platform implements its own
    """
    
    exact_mappings: dict[str, str] = Field(
        default_factory=lambda: {
            "analysts": "analyst",
            "viewers": "viewer",
            "admins": "admin",
            "administrators": "admin",
            "node_executors": "node_executor",
            "executors": "node_executor",
            "developers": "developer",
            "engineers": "developer",
            "members": "member",
            "users": "member",
        },
        description="Exact group name to role mapping (case-insensitive)"
    )
    
    pattern_mappings: dict[str, str] = Field(
        default_factory=lambda: {
            ".*admin.*": "admin",
            ".*analyst.*": "analyst",
            ".*executor.*": "node_executor",
            ".*(dev|engineer).*": "developer",
            ".*view.*": "viewer",
        },
        description="Regex pattern to role mapping (case-insensitive)"
    )
    
    default_role: str = Field(
        default="member",
        description="Default role when no mapping matches"
    )
    
    preserve_unmapped_groups: bool = Field(
        default=True,
        description="Keep unmapped group names as custom roles (sanitized)"
    )


class ProvisioningConfig(BaseModel):
    """SCIM provisioning configuration"""
    
    role_mapping: RoleMappingConfig = Field(
        default_factory=RoleMappingConfig,
        description="Group to role mapping configuration"
    )
