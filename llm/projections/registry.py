"""cost projector registry"""

from typing import Dict, Type, Optional
from optorch.logging import get_logger

logger = get_logger(__name__)


class CostProjectorRegistry:
    """registry for cost projection strategies"""
    
    _estimators: Dict[str, Type] = {}
    _default: Optional[str] = None
    
    @classmethod
    def register(cls, name: str, estimator_class: Type, is_default: bool = False):
        """register cost projector"""
        cls._estimators[name] = estimator_class
        if is_default:
            cls._default = name
        logger.debug(f"registered cost projector: {name} (default={is_default})")
    
    @classmethod
    def get(cls, name: Optional[str] = None) -> Type:
        """get projector class by name or default"""
        target = name or cls._default or "simple"
        estimator = cls._estimators.get(target)
        if not estimator:
            raise ValueError(f"cost projector not found: {target}")
        return estimator
    
    @classmethod
    def get_default(cls) -> Type:
        """get default projector"""
        return cls.get(cls._default)
