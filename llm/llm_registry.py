"""LLM registry for managing clients and pools"""
from typing import List
from optorch.llm.base_client import BaseLLMClient
from optorch.llm.llm_pool import LLMPool
from optorch.llm.pool import StrategyRegistry


class LLMRegistry:
    """Registry for managing single LLM clients and pools"""
    
    def __init__(self) -> None:
        self._clients: dict[str, BaseLLMClient] = {}
        self._pools: dict[str, LLMPool] = {}
    
    def register(self, name: str, client: BaseLLMClient):
        self._clients[name] = client
    
    def register_pool(
        self,
        name: str,
        clients: List[BaseLLMClient],
        strategy: str = "round_robin"
    ):
        """Register a pool of LLM clients with load balancing strategy"""
        if not StrategyRegistry.has(strategy):
            raise ValueError(f"Unknown strategy '{strategy}'. Available: round_robin, least_busy, weighted")
        
        strategy_instance = StrategyRegistry.get(strategy)
        pool = LLMPool(clients, strategy_instance, name)
        
        self._pools[name] = pool
    
    def get(self, name: str):
        """Get client or pool by name"""
        return self._pools.get(name) or self._clients.get(name)
    
    def has(self, name: str) -> bool:
        """Check if client or pool exists"""
        return name in self._clients or name in self._pools
    
    def list_clients(self) -> List[str]:
        """List all registered client names"""
        return list(self._clients.keys())
    
    def list_pools(self) -> List[str]:
        """List all registered pool names"""
        return list(self._pools.keys())
