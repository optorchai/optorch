"""Weighted load balancing strategy"""
from typing import Optional, Any
from optorch.llm.pool.base_strategy import LoadBalancingStrategy

class WeightedStrategy(LoadBalancingStrategy):
    """
    Weight-based selection for mixed provider pools.
    Faster/cheaper models get more requests.
    """
    
    def __init__(self, weights: Optional[dict[str, Any]] = None):
        self.weights = weights or {}
        self.index = 0
    
    async def select_client(self, clients, request_size):
        weighted_clients = []
        for client in clients:
            model = client.model or "default"
            weight = self.weights.get(model, 1)
            weighted_clients.extend([client] * weight)
        
        client = weighted_clients[self.index % len(weighted_clients)]
        self.index += 1
        return client
