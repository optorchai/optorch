"""protection configuration models"""

from pydantic import BaseModel, Field
from typing import Optional


class ProtectionConfig(BaseModel):
    """protection rule configuration - defines required permission for resource+action"""

    resource_type: str = Field(
        description="Type of resource (config, tool, route, workflow, etc.)"
    )

    resource_id: str = Field(
        description="Specific resource identifier (key name, tool name, route path, etc.)"
    )

    action: str = Field(
        description="Action being performed (read, update, execute, access, etc.)"
    )

    permission: str = Field(
        description="Required permission in 'resource:action' or 'resource:subresource:action' format"
    )

    description: Optional[str] = Field(
        default=None, description="Human-readable description"
    )
    
    ui_hint: Optional[str] = Field(
        default=None, description="UI hint (e.g., 'Admin only', 'Premium feature')"
    )

    enforcement: str = Field(
        default="block",
        description="Enforcement strategy: block | interactive | route | warn",
    )

    fallback: Optional[str] = Field(
        default=None,
        description="Route to this resource if denied (route enforcement only)",
    )

    interactive_approval: bool = Field(
        default=False, description="Enable interactive approval flow"
    )

    approver_role: Optional[str] = Field(
        default=None,
        description="Role required to approve (interactive enforcement only)",
    )
