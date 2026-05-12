"""reload strategy registry"""

from typing import Dict, Type, TYPE_CHECKING
from optorch.config.reload.strategy import ReloadStrategy
from optorch.config.reload.strategies import (
    TTLReloadStrategy,
    ManualReloadStrategy,
    AlwaysCheckReloadStrategy,
    NoReloadStrategy
)
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.config.provider import ConfigProvider

logger = get_logger(__name__)


class ReloadStrategyRegistry:
    """registry for reload strategies"""
    
    _strategies: Dict[str, Type] = {
        "ttl": TTLReloadStrategy,
        "manual": ManualReloadStrategy,
        "always": AlwaysCheckReloadStrategy,
        "none": NoReloadStrategy,
    }
    
    @classmethod
    def create(
        cls, 
        strategy_type: str, 
        provider: "ConfigProvider",
        **kwargs
    ) -> ReloadStrategy:
        """create reload strategy instance
        
        args:
            strategy_type: strategy name (ttl, manual, always, none)
            provider: config provider instance
            **kwargs: strategy-specific args (e.g., interval for ttl)
        """
        if strategy_type not in cls._strategies:
            logger.warning(f"unknown reload strategy: {strategy_type}, using manual")
            strategy_type = "manual"
        
        strategy_class = cls._strategies[strategy_type]
        
        if strategy_type == "ttl":
            interval = kwargs.get("interval", 60)
            return strategy_class(provider=provider, interval=interval)
        elif strategy_type in ("always", "manual", "none"):
            if strategy_type in ("always",):
                return strategy_class(provider=provider)
            return strategy_class()
        
        return strategy_class()
    
    @classmethod
    def register(cls, name: str, strategy_class: Type) -> None:
        """register custom reload strategy"""
        cls._strategies[name] = strategy_class
        logger.debug(f"registered reload strategy: {name}")
