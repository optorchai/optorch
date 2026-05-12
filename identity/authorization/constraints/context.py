"""context/environment constraint provider"""

from optorch.identity.authorization.constraints.provider import ConstraintProvider
from optorch.identity.authorization.constraints.config import ContextConstraintConfig, BaseConstraintConfig
from optorch.identity.authorization.constraints.models import ConstraintContext, SubjectContext, EnvironmentContext
import logging

logger = logging.getLogger(__name__)


class ContextConstraint(ConstraintProvider):
    """context/environment-based constraint"""
    
    def __init__(self, config: BaseConstraintConfig):
        if not isinstance(config, ContextConstraintConfig):
            raise TypeError(f"Expected ContextConstraintConfig, got {type(config).__name__}")
        self.config = config
    
    @property
    def name(self) -> str:
        return "context"
    
    def evaluate(self, context: ConstraintContext) -> bool:
        """evaluate context constraints"""
        subject = context.subject
        environment = context.environment
        
        # check cost limit
        if self.config.max_cost is not None:
            if not self._check_cost(environment):
                return False
        
        # check budget remaining
        if self.config.min_budget_remaining is not None:
            if not self._check_budget(environment):
                return False
        
        # check required roles (any)
        if self.config.required_roles:
            if not self._check_roles_any(subject):
                return False
        
        # check required roles (all)
        if self.config.required_all_roles:
            if not self._check_roles_all(subject):
                return False
        
        # check required attributes
        if self.config.required_attributes:
            if not self._check_attributes(subject):
                return False
        
        # check allowed actions
        if self.config.allowed_actions:
            if context.action not in self.config.allowed_actions:
                logger.debug(f"action {context.action} not in allowed list: {self.config.allowed_actions}")
                return False
        
        return True
    
    def _check_cost(self, environment: EnvironmentContext) -> bool:
        """check cost limit"""
        max_cost = self.config.max_cost
        if max_cost is None:
            return True
        
        estimated_cost = environment.estimated_cost
        
        if estimated_cost > max_cost:
            logger.debug(f"cost limit exceeded: {estimated_cost} > {max_cost}")
            return False
        
        return True
    
    def _check_budget(self, environment: EnvironmentContext) -> bool:
        """check budget remaining"""
        min_budget = self.config.min_budget_remaining
        if min_budget is None:
            return True
        
        remaining = environment.budget_remaining
        
        if remaining < min_budget:
            logger.debug(f"insufficient budget: {remaining} < {min_budget}")
            return False
        
        return True
    
    def _check_roles_any(self, subject: SubjectContext) -> bool:
        """check subject has at least one required role"""
        if not self.config.required_roles:
            return True
        
        subject_roles = subject.roles
        
        if not any(role in subject_roles for role in self.config.required_roles):
            logger.debug(f"missing required role (any of {self.config.required_roles})")
            return False
        
        return True
    
    def _check_roles_all(self, subject: SubjectContext) -> bool:
        """check subject has all required roles"""
        if not self.config.required_all_roles:
            return True
        
        subject_roles = subject.roles
        
        if not all(role in subject_roles for role in self.config.required_all_roles):
            logger.debug(f"missing required roles (all of {self.config.required_all_roles})")
            return False
        
        return True
    
    def _check_attributes(self, subject: SubjectContext) -> bool:
        """check subject has required attributes"""
        if not self.config.required_attributes:
            return True
        
        for attr, expected_value in self.config.required_attributes.items():
            subject_value = getattr(subject, attr, None) or subject.attributes.get(attr)
            if subject_value != expected_value:
                logger.debug(f"attribute mismatch: {attr} = {subject_value} != {expected_value}")
                return False
        
        return True
