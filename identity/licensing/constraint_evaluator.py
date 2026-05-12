"""ODRL complex constraint evaluator"""

import logging
from datetime import datetime, UTC
from typing import List
from optorch.identity.licensing.models import Constraint

logger = logging.getLogger(__name__)


class ConstraintEvaluator:
    """evaluate ODRL constraints with complex operators
    
    supports:
    - DateTime ranges (validFrom/validUntil)
    - usage counts with time windows
    - spatial constraints (geofence, country codes)
    """

    def evaluate(self, constraint: Constraint, usage_context: dict) -> bool:
        """evaluate constraint against usage context"""
        
        if constraint.left_operand == "dateTime":
            return self._evaluate_datetime(constraint, usage_context)
        
        if constraint.left_operand == "count":
            return self._evaluate_count(constraint, usage_context)
        
        if constraint.left_operand in ["spatial", "location", "country"]:
            return self._evaluate_spatial(constraint, usage_context)
        
        logger.warning(f"unknown constraint operand: {constraint.left_operand}")
        return False
    
    def _evaluate_datetime(self, constraint: Constraint, context: dict) -> bool:
        """check datetime constraints"""
        current_time = context.get("current_time", datetime.now(UTC))
        
        if isinstance(constraint.right_operand, str):
            target_time = datetime.fromisoformat(constraint.right_operand)
        else:
            target_time = constraint.right_operand
        
        if constraint.operator == "lteq":
            return current_time <= target_time
        elif constraint.operator == "gteq":
            return current_time >= target_time
        elif constraint.operator == "lt":
            return current_time < target_time
        elif constraint.operator == "gt":
            return current_time > target_time
        elif constraint.operator == "eq":
            return current_time == target_time
        else:
            logger.warning(f"unknown datetime operator: {constraint.operator}")
            return False
    
    def _evaluate_count(self, constraint: Constraint, context: dict) -> bool:
        """check usage count constraints with time windows"""
        current_count = context.get("usage_count", 0)
        
        if constraint.unit and "/" in constraint.unit:
            base_unit, time_window = constraint.unit.split("/")
            
            if time_window == "month":
                current_count = context.get("usage_count_monthly", current_count)
            elif time_window == "day":
                current_count = context.get("usage_count_daily", current_count)
            elif time_window == "hour":
                current_count = context.get("usage_count_hourly", current_count)
        
        limit = int(constraint.right_operand)
        
        if constraint.operator == "lteq":
            return current_count <= limit
        elif constraint.operator == "gteq":
            return current_count >= limit
        elif constraint.operator == "lt":
            return current_count < limit
        elif constraint.operator == "gt":
            return current_count > limit
        elif constraint.operator == "eq":
            return current_count == limit
        else:
            logger.warning(f"unknown count operator: {constraint.operator}")
            return False
    
    def _evaluate_spatial(self, constraint: Constraint, context: dict) -> bool:
        """check spatial/geofence constraints"""
        
        if constraint.left_operand == "country":
            current_country = context.get("country_code", "")
            allowed_countries = constraint.right_operand
            
            if isinstance(allowed_countries, str):
                allowed_countries = [allowed_countries]
            
            if constraint.operator == "eq":
                return current_country in allowed_countries
            elif constraint.operator == "neq":
                return current_country not in allowed_countries
            else:
                logger.warning(f"unknown country operator: {constraint.operator}")
                return False
        
        if constraint.left_operand == "spatial":
            lat = context.get("latitude")
            lon = context.get("longitude")
            
            if lat is None or lon is None:
                logger.warning("geofence check requires latitude/longitude in context")
                return False
            
            bounds = constraint.right_operand
            
            in_bounds = (
                bounds["min_lat"] <= lat <= bounds["max_lat"] and
                bounds["min_lon"] <= lon <= bounds["max_lon"]
            )
            
            if constraint.operator == "eq":
                return in_bounds
            elif constraint.operator == "neq":
                return not in_bounds
            else:
                logger.warning(f"unknown spatial operator: {constraint.operator}")
                return False
        
        return False
    
    def evaluate_all(self, constraints: List[Constraint], context: dict) -> bool:
        """all constraints must pass"""
        return all(self.evaluate(c, context) for c in constraints)
