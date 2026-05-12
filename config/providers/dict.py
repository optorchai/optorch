"""dict config provider - in-memory for testing"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from optorch.logging import get_logger
from optorch.errors.exceptions import ConfigurationError

logger = get_logger(__name__)


class DictConfigProvider:
    """in-memory config provider for testing"""
    
    def __init__(self, configs: Optional[Dict[str, Dict[str, Any]]] = None):
        """initialize with optional seed data
        
        args:
            configs: dict mapping namespace -> config data
        """
        self._configs: Dict[str, Dict[str, Any]] = configs.copy() if configs else {}
        self._timestamps: Dict[str, datetime] = {}
        logger.debug(f"dict provider initialized with {len(self._configs)} namespaces")
    
    def load(self, identifier: str) -> Dict[str, Any]:
        """load config from dict"""
        if identifier not in self._configs:
            raise ConfigurationError(
                f"config not found: {identifier}",
                details={
                    "identifier": identifier,
                    "available": list(self._configs.keys())
                }
            )
        return self._configs[identifier].copy()
    
    def discover(self, base_identifier: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """return all configs"""
        return {k: v.copy() for k, v in self._configs.items()}
    
    def list_namespaces(self, scope: Optional[str] = None) -> List[str]:
        """list namespaces"""
        namespaces = list(self._configs.keys())
        
        if scope:
            prefix = f"{scope}."
            return [ns.replace(prefix, "") for ns in namespaces if ns.startswith(prefix)]
        
        return namespaces
    
    def save(self, identifier: str, config: Dict[str, Any]) -> None:
        """save config to dict"""
        self._configs[identifier] = config.copy()
        self._timestamps[identifier] = datetime.now()
        logger.debug(f"saved config: {identifier}")
    
    def merge_overrides(
        self,
        namespace: str,
        overrides: Dict[str, Any] | str | List[str],
        isolate: bool = True
    ) -> Dict[str, Any]:
        """merge config overrides
        
        note: dict provider only supports dict overrides, not file paths
        """
        try:
            base = self.load(namespace)
        except ConfigurationError:
            base = {}
        
        if not isolate:
            result = base
        else:
            from optorch.config.merger import deep_merge
            result = deep_merge({}, base)
        
        if isinstance(overrides, dict):
            from optorch.config.merger import deep_merge
            return deep_merge(result, overrides)
        
        if isinstance(overrides, (str, list)):
            raise ConfigurationError(
                "dict provider does not support file path overrides",
                details={
                    "provider_type": "dict",
                    "reason": "file_paths_not_supported",
                    "override_type": type(overrides).__name__
                }
            )
        
        return result
    
    def get_timestamp(self, namespace: str) -> Optional[datetime]:
        """get last save time for namespace"""
        return self._timestamps.get(namespace)
    
    def clear(self) -> None:
        """clear all configs (testing helper)"""
        self._configs.clear()
        self._timestamps.clear()
