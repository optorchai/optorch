"""time-based constraint provider"""

from datetime import datetime, UTC
from optorch.identity.authorization.constraints.provider import ConstraintProvider
from optorch.identity.authorization.constraints.config import TimeConstraintConfig, BaseConstraintConfig
from optorch.identity.authorization.constraints.models import ConstraintContext
import logging

logger = logging.getLogger(__name__)


class TimeConstraint(ConstraintProvider):
    """time-based access control constraint"""
    
    def __init__(self, config: BaseConstraintConfig):
        if not isinstance(config, TimeConstraintConfig):
            raise TypeError(f"Expected TimeConstraintConfig, got {type(config).__name__}")
        self.config = config
    
    @property
    def name(self) -> str:
        return "time"
    
    def evaluate(self, context: ConstraintContext) -> bool:
        """evaluate time constraints"""
        now = context.environment.current_time or datetime.now(UTC)
        
        # check business hours
        if self.config.start_hour is not None and self.config.end_hour is not None:
            if not (self.config.start_hour <= now.hour < self.config.end_hour):
                logger.debug(f"outside business hours: {now.hour} not in [{self.config.start_hour}, {self.config.end_hour})")
                return False
        
        # check weekday restriction
        if self.config.weekday_only and now.weekday() >= 5:
            logger.debug(f"weekday only restriction failed: {now.weekday()}")
            return False
        
        # check time range
        if self.config.start_time and self.config.end_time:
            current_time = now.time()
            if not (self.config.start_time <= current_time <= self.config.end_time):
                logger.debug(f"outside time range: {current_time} not in [{self.config.start_time}, {self.config.end_time}]")
                return False
        
        # check after date
        if self.config.after_date and now < self.config.after_date:
            logger.debug(f"before required date: {now} < {self.config.after_date}")
            return False
        
        # check before date
        if self.config.before_date and now > self.config.before_date:
            logger.debug(f"after required date: {now} > {self.config.before_date}")
            return False
        
        return True
