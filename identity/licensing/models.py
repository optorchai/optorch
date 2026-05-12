"""ODRL 2.2 licensing models"""

from pydantic import BaseModel, Field
from datetime import datetime, UTC
from typing import Literal, List, Optional, Any


class Constraint(BaseModel):
    """ODRL Constraint - limit on permission"""
    left_operand: str  # "count" | "dateTime" | "spatial"
    operator: str  # "lteq" | "gteq" | "eq" | "neq" | "lt" | "gt"
    right_operand: Any  # value (10_000_000, datetime, etc.)
    unit: Optional[str] = None  # "tokens/month" | "deployments" | "users"
    data_type: Optional[str] = None
    status: Optional[str] = None


class Duty(BaseModel):
    """ODRL Duty - obligation"""
    action: str
    constraints: List[Constraint] = []
    consequence: Optional[List["Duty"]] = None


class Permission(BaseModel):
    """ODRL Permission - allowed action with constraints"""
    target: str  # asset: "feature:chatbot" | "feature:workflow"
    action: str  # "use" | "distribute" | "modify"
    constraints: List[Constraint] = []
    duty: Optional[Duty] = None


class Prohibition(BaseModel):
    """ODRL Prohibition - forbidden action"""
    target: str
    action: str
    remedy: Optional[List[Duty]] = None


class License(BaseModel):
    """ODRL 2.2 Agreement policy"""

    uid: str  # unique license id
    policy_type: Literal["Agreement", "Offer"] = "Agreement"
    assigner: str  # licensor (e.g., "optorch-inc")
    assignee: str  # organization id (licensee)
    permissions: List[Permission] = []
    prohibitions: List[Prohibition] = []
    obligations: List[Duty] = []
    valid_from: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime = Field(default_factory=lambda: datetime.now(UTC))
    signature: Optional[str] = None  # rsa signature
    metadata: dict = {}


class Decision(BaseModel):
    """License validation decision"""
    result: Literal["Permit", "Deny"]
    reason: str
