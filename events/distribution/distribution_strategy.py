"""Abstract distribution strategy"""
from abc import ABC, abstractmethod
from typing import List
from optorch.events.listener_entry import ListenerEntry


class DistributionStrategy(ABC):
    """Algorithm for distributing listeners to a backend"""
    
    @abstractmethod
    def distribute(
        self,
        listeners: List[ListenerEntry],
        backend: 'EventBackend'
    ) -> List[ListenerEntry]:
        """return listeners assigned to this backend"""
        pass
