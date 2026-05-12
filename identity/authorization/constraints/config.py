"""pydantic configs for constraints"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import time, datetime


class BaseConstraintConfig(BaseModel):
    """base configuration for all constraints"""
    pass


class TimeConstraintConfig(BaseConstraintConfig):
    """config for time-based constraints"""
    start_hour: int = Field(default=9, ge=0, le=23, description="business hours start")
    end_hour: int = Field(default=17, ge=0, le=23, description="business hours end")
    weekday_only: bool = Field(default=False, description="restrict to weekdays")
    start_time: Optional[time] = Field(default=None, description="specific start time")
    end_time: Optional[time] = Field(default=None, description="specific end time")
    after_date: Optional[datetime] = Field(default=None, description="must be after this date")
    before_date: Optional[datetime] = Field(default=None, description="must be before this date")
    timezone: Optional[str] = Field(default=None, description="timezone name")


class LocationConstraintConfig(BaseConstraintConfig):
    """config for location-based constraints"""
    allowed_countries: Optional[List[str]] = Field(default=None, description="ISO country code whitelist")
    blocked_countries: Optional[List[str]] = Field(default=None, description="ISO country code blacklist")
    allowed_ip_ranges: Optional[List[str]] = Field(default=None, description="CIDR blocks whitelist")
    geofence_bounds: Optional[dict[str, float]] = Field(
        default=None,
        description="rectangular bounds: min_lat, max_lat, min_lon, max_lon"
    )


class ResourceConstraintConfig(BaseConstraintConfig):
    """config for resource attribute constraints"""
    require_ownership: bool = Field(default=False, description="subject must own resource")
    require_same_org: bool = Field(default=False, description="subject and resource same org")
    min_clearance_level: Optional[int] = Field(default=None, description="minimum clearance level")
    required_tags: Optional[List[str]] = Field(default=None, description="resource must have these tags")


class ContextConstraintConfig(BaseConstraintConfig):
    """config for environment/context constraints"""
    max_cost: Optional[float] = Field(default=None, description="maximum operation cost")
    min_budget_remaining: Optional[float] = Field(default=None, description="minimum budget required")
    required_roles: Optional[List[str]] = Field(default=None, description="one of these roles required")
    required_all_roles: Optional[List[str]] = Field(default=None, description="all these roles required")
    required_attributes: Optional[dict[str, str]] = Field(default=None, description="user must have these attributes")
    allowed_actions: Optional[List[str]] = Field(default=None, description="whitelist of allowed actions")


class ConstraintConfig(BaseModel):
    """unified constraint configuration"""
    type: str = Field(description="constraint type: time, location, resource, context, custom")
    enabled: bool = Field(default=True, description="enable/disable constraint")
    time: Optional[TimeConstraintConfig] = None
    location: Optional[LocationConstraintConfig] = None
    resource: Optional[ResourceConstraintConfig] = None
    context: Optional[ContextConstraintConfig] = None
    custom_class: Optional[str] = Field(default=None, description="custom constraint class path")
    custom_config: Optional[dict[str, object]] = Field(default=None, description="custom constraint config")
