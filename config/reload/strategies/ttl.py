"""ttl reload strategy - check provider timestamp every N seconds"""

import time
from typing import Optional, Dict, TYPE_CHECKING
from datetime import datetime
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.config.provider import ConfigProvider

logger = get_logger(__name__)


class TTLReloadStrategy:
    """check timestamp every N seconds per namespace"""
    
    def __init__(self, provider: "ConfigProvider", interval: int = 60):
        self.provider = provider
        self.interval = interval
        self._last_check: Dict[str, float] = {}
    
    def should_reload(self, namespace: str, last_updated: Optional[datetime]) -> bool:
        """check if TTL expired and provider has newer version"""
        now = time.time()
        
        if now - self._last_check.get(namespace, 0) < self.interval:
            return False
        
        try:
            provider_timestamp = self.provider.get_timestamp(namespace)
            
            # provider doesn't support timestamps
            if provider_timestamp is None:
                return False
            
            # first load or provider has newer version
            if not last_updated or provider_timestamp > last_updated:
                return True
        except Exception as e:
            logger.debug(f"timestamp check failed for {namespace}: {e}")
        
        return False
    
    def mark_checked(self, namespace: str) -> None:
        """record check timestamp"""
        self._last_check[namespace] = time.time()

