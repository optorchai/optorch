"""location-based constraint provider"""

from optorch.identity.authorization.constraints.provider import ConstraintProvider
from optorch.identity.authorization.constraints.config import LocationConstraintConfig, BaseConstraintConfig
from optorch.identity.authorization.constraints.models import ConstraintContext
import logging

logger = logging.getLogger(__name__)


class LocationConstraint(ConstraintProvider):
    """location-based access control constraint"""
    
    def __init__(self, config: BaseConstraintConfig):
        if not isinstance(config, LocationConstraintConfig):
            raise TypeError(f"Expected LocationConstraintConfig, got {type(config).__name__}")
        self.config = config
    
    @property
    def name(self) -> str:
        return "location"
    
    def evaluate(self, context: ConstraintContext) -> bool:
        """evaluate location constraints"""
        
        # check country whitelist
        if self.config.allowed_countries:
            country = (context.environment.country_code or "").upper()
            if country not in [c.upper() for c in self.config.allowed_countries]:
                logger.debug(f"country {country} not in whitelist {self.config.allowed_countries}")
                return False
        
        # check country blacklist
        if self.config.blocked_countries:
            country = (context.environment.country_code or "").upper()
            if country in [c.upper() for c in self.config.blocked_countries]:
                logger.debug(f"country {country} in blacklist {self.config.blocked_countries}")
                return False
        
        # check IP ranges
        if self.config.allowed_ip_ranges:
            if not self._check_ip_ranges(context):
                return False
        
        # check geofence
        if self.config.geofence_bounds:
            if not self._check_geofence(context):
                return False
        
        return True
    
    def _check_ip_ranges(self, context: ConstraintContext) -> bool:
        """check if IP is in allowed CIDR ranges"""
        if not self.config.allowed_ip_ranges:
            return True
        
        try:
            import ipaddress
        except ImportError:
            logger.warning("ipaddress module required for IP range checks")
            return False
        
        client_ip = context.environment.ip_address
        if not client_ip:
            logger.warning("no ip_address in context")
            return False
        
        try:
            client = ipaddress.ip_address(client_ip)
            for cidr in self.config.allowed_ip_ranges:
                network = ipaddress.ip_network(cidr, strict=False)
                if client in network:
                    return True
            logger.debug(f"IP {client_ip} not in allowed ranges {self.config.allowed_ip_ranges}")
            return False
        except ValueError as e:
            logger.error(f"invalid IP or CIDR: {e}")
            return False
    
    def _check_geofence(self, context: ConstraintContext) -> bool:
        """check if coordinates within bounds"""
        if not self.config.geofence_bounds:
            return True
        
        lat = context.environment.latitude
        lon = context.environment.longitude
        
        if lat is None or lon is None:
            logger.warning("geofence requires latitude/longitude in context")
            return False
        
        bounds = self.config.geofence_bounds
        in_bounds = (
            bounds["min_lat"] <= lat <= bounds["max_lat"] and
            bounds["min_lon"] <= lon <= bounds["max_lon"]
        )
        
        if not in_bounds:
            logger.debug(f"coordinates ({lat}, {lon}) outside geofence {bounds}")
        
        return in_bounds
