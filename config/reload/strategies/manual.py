"""manual reload strategy - no automatic checks"""

from typing import Optional
from datetime import datetime


class ManualReloadStrategy:
    """never auto-reload - only via explicit reload_namespace() calls"""
    
    def should_reload(self, namespace: str, last_updated: Optional[datetime]) -> bool:
        """always return False - no automatic reload"""
        return False
    
    def mark_checked(self, namespace: str) -> None:
        """noop - no checks to track"""
        pass
