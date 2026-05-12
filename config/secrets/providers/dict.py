"""dict secret provider - in-memory for testing"""

from typing import Optional, Dict, List
from optorch.logging import get_logger

logger = get_logger(__name__)


class DictSecretProvider:
    """in-memory secret storage for testing"""
    
    def __init__(self, secrets: Optional[Dict[str, str]] = None):
        """initialize with optional seed data"""
        self._secrets: Dict[str, str] = secrets.copy() if secrets else {}
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """get secret from dict"""
        return self._secrets.get(key, default)
    
    def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """batch get from dict"""
        return {key: self._secrets.get(key) for key in keys}
    
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """list keys (optionally filtered)"""
        if prefix:
            return [k for k in self._secrets.keys() if k.startswith(prefix)]
        return list(self._secrets.keys())
    
    def set(self, key: str, value: str) -> None:
        """set secret in dict"""
        self._secrets[key] = value
        logger.debug(f"set secret: {key}")
    
    def clear(self) -> None:
        """clear all secrets (testing helper)"""
        self._secrets.clear()
