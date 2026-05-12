"""secret provider protocol - backend abstraction for secrets"""

from typing import Protocol, Optional, Dict, List, runtime_checkable


@runtime_checkable
class SecretProvider(Protocol):
    """protocol for secret backends (Environment, Vault, AWS, etc.)"""
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """get single secret
        
        args:
            key: secret key (e.g., "OPENAI_API_KEY", "database/password")
            default: default value if not found
        
        returns:
            secret value or default
        
        example:
            api_key = provider.get("OPENAI_API_KEY")
            db_pass = provider.get("DB_PASSWORD", "default_pass")
        """
        ...
    
    def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """batch get secrets
        
        args:
            keys: list of secret keys
        
        returns:
            dict mapping keys to values (None for missing)
        
        example:
            secrets = provider.get_many(["API_KEY", "DB_PASS"])
            # {"API_KEY": "sk-...", "DB_PASS": "xyz"}
        """
        ...
    
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """list available secret keys
        
        args:
            prefix: optional prefix filter
        
        returns:
            list of secret key names
        
        example:
            keys = provider.list_keys(prefix="OPENAI")
            # ["OPENAI_API_KEY", "OPENAI_API_KEY_2"]
        """
        ...
    
    def set(self, key: str, value: str) -> None:
        """set secret
        
        args:
            key: secret key
            value: secret value
        
        raises:
            NotImplementedError: if provider is read-only
        
        example:
            provider.set("TEST_KEY", "test_value")
        """
        ...
