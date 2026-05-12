"""no reload strategy - hot reload disabled"""

from typing import Optional
from datetime import datetime


class NoReloadStrategy:
    """hot reload completely disabled"""
    
    def should_reload(self, namespace: str, last_updated: Optional[datetime]) -> bool:
        """always return False"""
        return False
    
    def mark_checked(self, namespace: str) -> None:
        """noop"""
        pass
