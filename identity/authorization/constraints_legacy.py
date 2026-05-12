"""ABAC constraint helpers - common patterns for attribute-based access control

inspired by ODRL constraint evaluator but for authorization contexts
"""

from datetime import datetime, time, UTC
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TimeConstraints:
    """time-based access control helpers"""
    
    @staticmethod
    def business_hours(
        start_hour: int = 9,
        end_hour: int = 17,
        timezone: Optional[str] = None
    ) -> bool:
        """check if current time is within business hours
        
        Args:
            start_hour: Business hours start (0-23)
            end_hour: Business hours end (0-23)
            timezone: Optional timezone name (defaults to UTC)
        
        Returns:
            True if within business hours
        """
        now = datetime.now(UTC)
        return start_hour <= now.hour < end_hour
    
    @staticmethod
    def weekday_only() -> bool:
        """check if current day is weekday (monday-friday)"""
        now = datetime.now(UTC)
        return now.weekday() < 5  # 0=Monday, 6=Sunday
    
    @staticmethod
    def time_range(start: time, end: time, current_time: Optional[datetime] = None) -> bool:
        """check if time is within range
        
        Args:
            start: Start time
            end: End time
            current_time: Optional current time (defaults to now)
        
        Returns:
            True if within range
        """
        if current_time is None:
            current_time = datetime.now(UTC)
        
        current = current_time.time()
        return start <= current <= end
    
    @staticmethod
    def after_date(date: datetime, current_time: Optional[datetime] = None) -> bool:
        """check if current time is after date"""
        if current_time is None:
            current_time = datetime.now(UTC)
        return current_time >= date
    
    @staticmethod
    def before_date(date: datetime, current_time: Optional[datetime] = None) -> bool:
        """check if current time is before date"""
        if current_time is None:
            current_time = datetime.now(UTC)
        return current_time <= date


class LocationConstraints:
    """location-based access control helpers"""
    
    @staticmethod
    def country_allowed(allowed: List[str], context: Dict[str, Any]) -> bool:
        """check if current country is in allowed list
        
        Args:
            allowed: List of ISO country codes (e.g., ["US", "CA", "GB"])
            context: Request context with country_code field
        
        Returns:
            True if country allowed
        """
        current_country = context.get("country_code", "").upper()
        return current_country in [c.upper() for c in allowed]
    
    @staticmethod
    def country_blocked(blocked: List[str], context: Dict[str, Any]) -> bool:
        """check if current country is NOT in blocked list"""
        current_country = context.get("country_code", "").upper()
        return current_country not in [c.upper() for c in blocked]
    
    @staticmethod
    def ip_range(allowed_ranges: List[str], context: Dict[str, Any]) -> bool:
        """check if IP is in allowed CIDR ranges
        
        Args:
            allowed_ranges: List of CIDR blocks (e.g., ["10.0.0.0/8", "192.168.0.0/16"])
            context: Request context with ip_address field
        """
        try:
            import ipaddress
        except ImportError:
            logger.warning("ipaddress module required for IP range checks")
            return False
        
        client_ip = context.get("ip_address")
        if not client_ip:
            logger.warning("no ip_address in context")
            return False
        
        try:
            client = ipaddress.ip_address(client_ip)
            for cidr in allowed_ranges:
                network = ipaddress.ip_network(cidr, strict=False)
                if client in network:
                    return True
            return False
        except ValueError as e:
            logger.error(f"invalid IP or CIDR: {e}")
            return False
    
    @staticmethod
    def geofence(
        bounds: Dict[str, float],
        context: Dict[str, Any]
    ) -> bool:
        """check if coordinates are within rectangular bounds
        
        Args:
            bounds: {"min_lat": float, "max_lat": float, "min_lon": float, "max_lon": float}
            context: Request context with latitude/longitude fields
        
        Returns:
            True if within bounds
        """
        lat = context.get("latitude")
        lon = context.get("longitude")
        
        if lat is None or lon is None:
            logger.warning("geofence requires latitude/longitude in context")
            return False
        
        return (
            bounds["min_lat"] <= lat <= bounds["max_lat"] and
            bounds["min_lon"] <= lon <= bounds["max_lon"]
        )


class ResourceConstraints:
    """resource attribute-based constraints"""
    
    @staticmethod
    def owned_by(subject: Dict[str, Any], resource: Dict[str, Any]) -> bool:
        """check if subject owns resource"""
        subject_id = subject.get("user_id") or subject.get("id")
        resource_owner = resource.get("owner") or resource.get("owner_id")
        return subject_id == resource_owner
    
    @staticmethod
    def same_org(subject: Dict[str, Any], resource: Dict[str, Any]) -> bool:
        """check if subject and resource are in same organization"""
        return subject.get("org_id") == resource.get("org_id")
    
    @staticmethod
    def sensitivity_level(
        required_clearance: int,
        subject: Dict[str, Any],
        resource: Dict[str, Any]
    ) -> bool:
        """check if subject has required clearance for resource sensitivity
        
        Args:
            required_clearance: Minimum clearance level required
            subject: Subject with clearance_level attribute
            resource: Resource with sensitivity_level attribute
        
        Returns:
            True if clearance >= sensitivity
        """
        subject_clearance = subject.get("clearance_level", 0)
        resource_sensitivity = resource.get("sensitivity_level", 0)
        
        return subject_clearance >= max(required_clearance, resource_sensitivity)
    
    @staticmethod
    def tag_match(required_tags: List[str], resource: Dict[str, Any]) -> bool:
        """check if resource has all required tags"""
        resource_tags = resource.get("tags", [])
        return all(tag in resource_tags for tag in required_tags)


class ContextConstraints:
    """environment/context-based constraints"""
    
    @staticmethod
    def cost_limit(max_cost: float, context: Dict[str, Any]) -> bool:
        """check if cost is below limit"""
        current_cost = context.get("estimated_cost", 0)
        return current_cost <= max_cost
    
    @staticmethod
    def budget_available(required_amount: float, context: Dict[str, Any]) -> bool:
        """check if budget has enough remaining"""
        remaining = context.get("budget_remaining", 0)
        return remaining >= required_amount
    
    @staticmethod
    def user_attribute(
        attribute: str,
        expected_value: Any,
        subject: Dict[str, Any]
    ) -> bool:
        """check if user has specific attribute value"""
        return subject.get(attribute) == expected_value
    
    @staticmethod
    def role_in(required_roles: List[str], subject: Dict[str, Any]) -> bool:
        """check if subject has at least one of required roles"""
        subject_roles = subject.get("roles", [])
        return any(role in subject_roles for role in required_roles)
    
    @staticmethod
    def all_roles(required_roles: List[str], subject: Dict[str, Any]) -> bool:
        """check if subject has ALL required roles"""
        subject_roles = subject.get("roles", [])
        return all(role in subject_roles for role in required_roles)


class ConstraintBuilder:
    """fluent API for building complex ABAC constraints"""
    
    def __init__(self):
        self.checks: List[Tuple[callable, tuple, dict]] = []
    
    def time_constraint(self, func: callable, *args, **kwargs) -> "ConstraintBuilder":
        """add time constraint"""
        self.checks.append((func, args, kwargs))
        return self
    
    def location_constraint(self, func: callable, *args, **kwargs) -> "ConstraintBuilder":
        """add location constraint"""
        self.checks.append((func, args, kwargs))
        return self
    
    def resource_constraint(self, func: callable, *args, **kwargs) -> "ConstraintBuilder":
        """add resource constraint"""
        self.checks.append((func, args, kwargs))
        return self
    
    def context_constraint(self, func: callable, *args, **kwargs) -> "ConstraintBuilder":
        """add context constraint"""
        self.checks.append((func, args, kwargs))
        return self
    
    def custom(self, func: callable, *args, **kwargs) -> "ConstraintBuilder":
        """add custom constraint function"""
        self.checks.append((func, args, kwargs))
        return self
    
    def evaluate(self) -> bool:
        """evaluate all constraints (AND logic)"""
        return all(func(*args, **kwargs) for func, args, kwargs in self.checks)
    
    def evaluate_any(self) -> bool:
        """evaluate with OR logic - pass if any constraint passes"""
        return any(func(*args, **kwargs) for func, args, kwargs in self.checks)
