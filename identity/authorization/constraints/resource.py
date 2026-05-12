"""resource attribute constraint provider"""

from optorch.identity.authorization.constraints.provider import ConstraintProvider
from optorch.identity.authorization.constraints.config import ResourceConstraintConfig, BaseConstraintConfig
from optorch.identity.authorization.constraints.models import ConstraintContext, SubjectContext, ResourceContext
import logging

logger = logging.getLogger(__name__)


class ResourceConstraint(ConstraintProvider):
    """resource attribute access control constraint"""
    
    def __init__(self, config: BaseConstraintConfig):
        if not isinstance(config, ResourceConstraintConfig):
            raise TypeError(f"Expected ResourceConstraintConfig, got {type(config).__name__}")
        self.config = config
    
    @property
    def name(self) -> str:
        return "resource"
    
    def evaluate(self, context: ConstraintContext) -> bool:
        """evaluate resource constraints"""
        subject = context.subject
        resource = context.resource
        
        # check ownership requirement
        if self.config.require_ownership:
            if not self._check_ownership(subject, resource):
                return False
        
        # check same org requirement
        if self.config.require_same_org:
            if not self._check_same_org(subject, resource):
                return False
        
        # check clearance level
        if self.config.min_clearance_level is not None:
            if not self._check_clearance(subject, resource):
                return False
        
        # check required tags
        if self.config.required_tags:
            if not self._check_tags(resource):
                return False
        
        return True
    
    def _check_ownership(self, subject: SubjectContext, resource: ResourceContext) -> bool:
        """check if subject owns resource"""
        subject_id = subject.user_id
        resource_owner = resource.owner_id
        
        if subject_id != resource_owner:
            logger.debug(f"ownership check failed: {subject_id} != {resource_owner}")
            return False
        
        return True
    
    def _check_same_org(self, subject: SubjectContext, resource: ResourceContext) -> bool:
        """check if subject and resource in same org"""
        subject_org = subject.org_id
        resource_org = resource.org_id
        
        if subject_org != resource_org:
            logger.debug(f"org check failed: {subject_org} != {resource_org}")
            return False
        
        return True
    
    def _check_clearance(self, subject: SubjectContext, resource: ResourceContext) -> bool:
        """check clearance level"""
        subject_clearance = subject.clearance_level
        resource_sensitivity = resource.sensitivity_level
        
        min_required = self.config.min_clearance_level or 0
        required = max(min_required, resource_sensitivity)
        
        if subject_clearance < required:
            logger.debug(f"clearance check failed: {subject_clearance} < {required}")
            return False
        
        return True
    
    def _check_tags(self, resource: ResourceContext) -> bool:
        """check resource has required tags"""
        if not self.config.required_tags:
            return True
        
        resource_tags = resource.tags
        
        for tag in self.config.required_tags:
            if tag not in resource_tags:
                logger.debug(f"missing required tag: {tag}")
                return False
        
        return True
