"""XACML 3.0 authorization models"""

from pydantic import BaseModel
from typing import Literal, Optional, List


class Decision(BaseModel):
    """Authorization decision (XACML-aligned)"""
    result: Literal["Permit", "Deny", "NotApplicable", "Indeterminate"]
    reason: Optional[str] = None  # why decision was made
    obligations: List[str] = []  # required actions (e.g., "log_access")
    advice: List[str] = []  # optional actions

    @property
    def permit(self) -> bool:
        """Convenience property"""
        return self.result == "Permit"

    @property
    def deny(self) -> bool:
        return self.result == "Deny"


class Permission(BaseModel):
    """Permission definition"""
    subject: str  # user or role
    resource: str  # resource identifier
    action: str  # action to perform


class Role(BaseModel):
    """Role definition"""
    name: str
    permissions: List[Permission] = []


class Resource(BaseModel):
    """Resource definition"""
    type: str
    id: str
    owner: Optional[str] = None
    org_id: Optional[str] = None
