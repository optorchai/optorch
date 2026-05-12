"""Auto-discovery registry for resilience strategies"""
from typing import Dict, Type
from pathlib import Path
from optorch.storage.resilience.base import ResilienceStrategy
from optorch.logging import get_logger

logger = get_logger(__name__)


class ResilienceRegistry:
    """Auto-discover and register resilience strategies"""
    
    def __init__(self):
        self._strategies: Dict[str, Type[ResilienceStrategy]] = {}
        self._discover_builtin_strategies()
    
    def _discover_builtin_strategies(self):
        """Auto-discover built-in strategies from optorch/storage/resilience/strategies/"""
        strategies_path = Path(__file__).parent / "strategies"
        
        if not strategies_path.exists():
            return
        
        for strategy_file in strategies_path.glob("*.py"):
            if strategy_file.stem.startswith("_"):
                continue
            
            module_name = f"optorch.storage.resilience.strategies.{strategy_file.stem}"
            try:
                module = __import__(module_name, fromlist=["*"])
                
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, ResilienceStrategy) and 
                        attr is not ResilienceStrategy):
                        
                        strategy_name = strategy_file.stem
                        self._strategies[strategy_name] = attr
                        logger.debug(f"registered resilience strategy: {strategy_name}")
            except Exception as e:
                logger.warning(f"failed to load resilience strategy from {strategy_file}: {e}")
    
    def register(self, name: str, strategy_class: Type[ResilienceStrategy]):
        """Manually register custom resilience strategy"""
        self._strategies[name] = strategy_class
        logger.info(f"registered custom resilience strategy: {name}")
    
    def get(self, name: str) -> Type[ResilienceStrategy]:
        """Get strategy class by name"""
        if name not in self._strategies:
            raise ValueError(f"Unknown resilience strategy: {name}")
        return self._strategies[name]
    
    def get_all(self) -> Dict[str, Type[ResilienceStrategy]]:
        """Get all registered strategies"""
        return self._strategies.copy()
