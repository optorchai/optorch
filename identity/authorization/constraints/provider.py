"""base constraint provider - ABC for type-safe constraint implementations"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.identity.authorization.constraints.models import ConstraintContext


class ConstraintProvider(ABC):
    """base class for constraint providers
    
    all constraints must implement evaluate method and name property
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """constraint type name"""
        ...
    
    @abstractmethod
    def evaluate(self, context: 'ConstraintContext') -> bool:
        """evaluate constraint against context
        
        Args:
            context: typed constraint context (subject, resource, action, environment)
        
        Returns:
            True if constraint passes, False otherwise
        """
        ...
        """constraint provider name"""
        ...
