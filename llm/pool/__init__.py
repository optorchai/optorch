"""
Load balancing strategies for LLM pools.
"""
from typing import Type
from optorch.llm.pool.base_strategy import LoadBalancingStrategy
from optorch.llm.pool.round_robin_strategy import RoundRobinStrategy
from optorch.llm.pool.least_busy_strategy import LeastBusyStrategy
from optorch.llm.pool.weighted_strategy import WeightedStrategy
from optorch.registry import Registry

class StrategyRegistry:
    """Registry for load balancing strategies"""
    _strategies = Registry[Type[LoadBalancingStrategy]]()
    
    @classmethod
    def register(cls, name: str, strategy: Type[LoadBalancingStrategy]):
        """Register a load balancing strategy class"""
        cls._strategies.register(name, strategy)
    
    @classmethod
    def get(cls, name: str) -> LoadBalancingStrategy:
        """Get strategy instance by name"""
        strategy_class = cls._strategies.get(name)
        return strategy_class()
    
    @classmethod
    def has(cls, name: str) -> bool:
        """Check if strategy exists"""
        return cls._strategies.has(name)


StrategyRegistry.register("round_robin", RoundRobinStrategy)
StrategyRegistry.register("least_busy", LeastBusyStrategy)
StrategyRegistry.register("weighted", WeightedStrategy)

__all__ = [
    "LoadBalancingStrategy",
    "RoundRobinStrategy",
    "LeastBusyStrategy",
    "WeightedStrategy",
    "StrategyRegistry"
]
