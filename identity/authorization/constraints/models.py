"""typed context models for constraint evaluation"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class SubjectContext(BaseModel):
    """subject (user/principal) context for constraint evaluation"""
    
    user_id: Optional[str] = Field(default=None, description="user identifier")
    org_id: Optional[str] = Field(default=None, description="organization identifier")
    roles: List[str] = Field(default_factory=list, description="user roles")
    clearance_level: int = Field(default=0, description="security clearance level")
    department: Optional[str] = Field(default=None, description="user department")
    verified: bool = Field(default=False, description="user verification status")
    attributes: dict[str, str | int | bool] = Field(default_factory=dict, description="additional user attributes")


class ResourceContext(BaseModel):
    """resource context for constraint evaluation"""
    
    resource_id: Optional[str] = Field(default=None, description="resource identifier")
    resource_type: Optional[str] = Field(default=None, description="resource type")
    owner_id: Optional[str] = Field(default=None, description="resource owner")
    org_id: Optional[str] = Field(default=None, description="resource organization")
    sensitivity_level: int = Field(default=0, description="resource sensitivity/classification")
    tags: List[str] = Field(default_factory=list, description="resource tags")
    attributes: dict[str, str | int | bool] = Field(default_factory=dict, description="additional resource attributes")


class EnvironmentContext(BaseModel):
    """environment context for constraint evaluation"""
    
    current_time: Optional[datetime] = Field(default=None, description="request timestamp")
    ip_address: Optional[str] = Field(default=None, description="client IP address")
    country_code: Optional[str] = Field(default=None, description="ISO country code")
    latitude: Optional[float] = Field(default=None, description="client latitude")
    longitude: Optional[float] = Field(default=None, description="client longitude")
    user_agent: Optional[str] = Field(default=None, description="client user agent")
    estimated_cost: float = Field(default=0.0, description="estimated operation cost")
    budget_remaining: float = Field(default=0.0, description="remaining budget")
    attributes: dict[str, str | int | bool | float] = Field(default_factory=dict, description="additional environment attributes")


class ConstraintContext(BaseModel):
    """complete context for constraint evaluation
    
    combines subject, resource, action, and environment
    used by all constraint providers for evaluation
    """
    
    subject: SubjectContext = Field(default_factory=SubjectContext, description="user/principal context")
    resource: ResourceContext = Field(default_factory=ResourceContext, description="resource being accessed")
    action: Optional[str] = Field(default=None, description="action being performed")
    environment: EnvironmentContext = Field(default_factory=EnvironmentContext, description="environmental context")
    
    def to_dict(self) -> dict:
        """convert to legacy dict format for backwards compatibility"""
        return {
            "subject": self.subject.model_dump(),
            "resource": self.resource.model_dump(),
            "action": self.action,
            "environment": self.environment.model_dump(),
            "current_time": self.environment.current_time,
            "ip_address": self.environment.ip_address,
            "country_code": self.environment.country_code,
            "latitude": self.environment.latitude,
            "longitude": self.environment.longitude,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConstraintContext':
        """create from legacy dict format"""
        return cls(
            subject=SubjectContext(**data.get("subject", {})),
            resource=ResourceContext(**data.get("resource", {})),
            action=data.get("action"),
            environment=EnvironmentContext(
                current_time=data.get("current_time") or data.get("environment", {}).get("current_time"),
                ip_address=data.get("ip_address") or data.get("environment", {}).get("ip_address"),
                country_code=data.get("country_code") or data.get("environment", {}).get("country_code"),
                latitude=data.get("latitude") or data.get("environment", {}).get("latitude"),
                longitude=data.get("longitude") or data.get("environment", {}).get("longitude"),
                **(data.get("environment", {}))
            )
        )
