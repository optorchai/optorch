"""Tag-based routing strategy"""
from typing import List, TYPE_CHECKING
from optorch.events.distribution.distribution_strategy import DistributionStrategy
from optorch.events.listener_entry import ListenerEntry

if TYPE_CHECKING:
    from optorch.events.backend import EventBackend


class TagBasedStrategy(DistributionStrategy):
    """Route by tag matching
    
    Rules:
    - Untagged listener → all backends (broadcast)
    - Empty backend tags → accepts all listeners
    - Tagged → match any overlap
    """
    
    def distribute(
        self,
        listeners: List[ListenerEntry],
        backend: 'EventBackend'
    ) -> List[ListenerEntry]:
        """filter listeners for this backend by tag matching"""
        result = []
        
        for entry in listeners:
            # empty backend tags = accept all
            if not backend.accept_tags:
                result.append(entry)
            # untagged listener = broadcast to all
            elif entry.tags is None:
                result.append(entry)
            # check tag overlap
            elif entry.has_any_tag(backend.accept_tags):
                result.append(entry)
        
        return result
