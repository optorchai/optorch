"""reload strategy protocol"""

from typing import Protocol, Optional
from datetime import datetime


class ReloadStrategy(Protocol):
    """strategy for config hot-reload behavior"""
    
    def should_reload(self, namespace: str, last_updated: Optional[datetime]) -> bool:
        """check if namespace should be reloaded
        
        args:
            namespace: config namespace to check
            last_updated: last known update time from cache
            
        returns:
            True if config should be reloaded from database
        """
        ...
    
    def mark_checked(self, namespace: str) -> None:
        """record that check happened for this namespace"""
        ...
