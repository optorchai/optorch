"""always check reload strategy - check provider on every access"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.config.provider import ConfigProvider

logger = get_logger(__name__)


class AlwaysCheckReloadStrategy:
    """check provider timestamp on every config access - for development"""
    
    def __init__(self, provider: "ConfigProvider"):
        self.provider = provider
    
    def should_reload(self, namespace: str, last_updated: Optional[datetime]) -> bool:
        """always check provider for latest timestamp"""
        try:
            provider_timestamp = self.provider.get_timestamp(namespace)
            
            if provider_timestamp is None:
                return False
            
            # first load or provider has newer version
            if not last_updated or provider_timestamp > last_updated:
                return True
        except Exception as e:
            logger.debug(f"timestamp check failed for {namespace}: {e}")
        
        return False
    
    def mark_checked(self, namespace: str) -> None:
        """noop - checks happen every time"""
        pass
