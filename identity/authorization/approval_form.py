"""authorization approval form for interactive enforcement"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, Optional


class AuthorizationApprovalForm(BaseModel):
    """approval form for restricted authorization decisions
    
    used when policy requires manual approval for high-risk operations
    pattern matches budget.BudgetApprovalForm
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "subject": "user:john@example.com",
                "resource": "database:prod-customer-data",
                "action": "delete",
                "justification": "GDPR deletion request ticket #12345",
                "risk_level": "high",
                "duration": 3600,
                "context": {
                    "ticket_id": "12345",
                    "approver_role": "data_protection_officer"
                }
            }
        }
    )
    
    subject: str = Field(..., description="User requesting access")
    resource: str = Field(..., description="Resource being accessed")
    action: str = Field(..., description="Action being performed")
    
    justification: str = Field(
        ...,
        description="Business justification for access"
    )
    
    risk_level: str = Field(
        default="medium",
        description="Risk assessment (low/medium/high/critical)"
    )
    
    duration: Optional[int] = Field(
        None,
        description="Temporary access duration in seconds (None = permanent)"
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for approval decision"
    )
