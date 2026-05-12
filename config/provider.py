"""config provider protocol - backend abstraction for config storage"""

from typing import Protocol, Dict, Any, Optional, List, runtime_checkable
from datetime import datetime


@runtime_checkable
class ConfigProvider(Protocol):
    """protocol for config backends (YAML, Database, Consul, etc.)"""
    
    def load(self, identifier: str) -> Dict[str, Any]:
        """load config by namespace identifier
        
        args:
            identifier: namespace key (e.g., "optorch", "nodes", "interactions.budget")
        
        returns:
            config dictionary
        
        raises:
            ConfigurationError: if config not found or load fails
        
        example:
            config = provider.load("optorch")
            nodes = provider.load("nodes")
        """
        ...
    
    def discover(self, base_identifier: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """discover all available configs
        
        args:
            base_identifier: optional base path to discover from
        
        returns:
            dict mapping namespace identifiers to configs
        
        example:
            configs = provider.discover()
            # {"optorch": {...}, "nodes": {...}, "interactions.budget": {...}}
        """
        ...
    
    def list_namespaces(self, scope: Optional[str] = None) -> List[str]:
        """list config namespaces
        
        args:
            scope: optional scope filter (e.g., "interactions" returns ["budget", "tariff"])
        
        returns:
            list of namespace names (clean names, not prefixed)
        
        examples:
            list_namespaces() → ["optorch", "nodes", "interactions.budget"]
            list_namespaces(scope="interactions") → ["budget", "tariff"]
        """
        ...
    
    def save(self, identifier: str, config: Dict[str, Any]) -> None:
        """persist config
        
        args:
            identifier: namespace identifier
            config: config data to save
        
        raises:
            NotImplementedError: if provider is read-only
        
        example:
            provider.save("budget", {"limit": 1000})
        """
        ...
    
    def merge_overrides(
        self,
        namespace: str,
        overrides: Dict[str, Any] | str | List[str],
        isolate: bool = True
    ) -> Dict[str, Any]:
        """merge config overrides without modifying base
        
        args:
            namespace: target namespace to merge into
            overrides: override data - dict (REQUIRED all providers) or file path(s) (optional)
            isolate: if True, return new dict without touching base config
        
        returns:
            merged config dictionary
        
        raises:
            ConfigurationError: if file paths passed to non-file provider
        
        implementation requirements:
            - dict overrides: MUST support (all providers)
            - file path overrides: OPTIONAL (file-based providers only)
            - non-file providers MUST raise ConfigurationError with details:
              {"provider_type": "database", "reason": "file_paths_not_supported"}
        
        note:
            critical for library mode - must not pollute ConfigManager
        
        examples:
            # dict override (all providers)
            merged = provider.merge_overrides("budget", {"limit": 5000}, isolate=True)
            
            # file override (YAML only)
            merged = provider.merge_overrides("budget", "/tmp/override.yaml", isolate=True)
        """
        ...
    
    def get_timestamp(self, namespace: str) -> Optional[datetime]:
        """get last-updated timestamp for namespace
        
        args:
            namespace: namespace identifier
        
        returns:
            timestamp of last update, or None if unsupported/not found
        
        note:
            providers that don't support hot-reload should return None
            used by reload strategies to check if config changed
        
        example:
            timestamp = provider.get_timestamp("tools")
            if timestamp and timestamp > last_check:
                reload()
        """
        return None
