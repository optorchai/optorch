"""Least busy load balancing strategy"""
from optorch.llm.pool.base_strategy import LoadBalancingStrategy

class LeastBusyStrategy(LoadBalancingStrategy):
    """Select client with fewest active requests"""
    
    async def select_client(self, clients, request_size):
        return min(clients, key=lambda c: c.active_requests)
