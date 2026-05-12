"""Round-robin load balancing strategy"""
from optorch.llm.pool.base_strategy import LoadBalancingStrategy

class RoundRobinStrategy(LoadBalancingStrategy):
    """Distribute requests evenly across all clients"""
    
    def __init__(self) -> None:
        self.index = 0
    
    async def select_client(self, clients, request_size):
        client = clients[self.index % len(clients)]
        self.index += 1
        return client
