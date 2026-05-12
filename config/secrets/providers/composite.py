"""composite secret provider - fallback chain pattern"""

from typing import Optional, Dict, List
from optorch.logging import get_logger
from optorch.config.secrets.provider import SecretProvider

logger = get_logger(__name__)


class CompositeSecretProvider:
    """chain multiple secret providers with fallback
    
    tries providers in order, returns first successful result
    
    example:
        provider = CompositeSecretProvider([
            VaultSecretProvider(...),      # production secrets
            EnvironmentSecretProvider()    # fallback to env
        ])
    """
    
    def __init__(self, providers: List[SecretProvider]):
        """initialize with ordered list of providers"""
        if not providers:
            raise ValueError("composite provider needs at least one provider")
        self.providers = providers
        logger.debug(f"composite provider with {len(providers)} backends")
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """try each provider until one succeeds"""
        for i, provider in enumerate(self.providers):
            try:
                value = provider.get(key)
                if value is not None:
                    logger.debug(f"secret '{key}' found in provider {i}")
                    return value
            except Exception as e:
                logger.debug(f"provider {i} failed for '{key}': {e}")
                continue
        
        logger.debug(f"secret '{key}' not found in any provider, using default")
        return default
    
    def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """batch get with fallback"""
        return {key: self.get(key) for key in keys}
    
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """list keys from all providers (union)"""
        all_keys = set()
        for provider in self.providers:
            try:
                keys = provider.list_keys(prefix=prefix)
                all_keys.update(keys)
            except Exception as e:
                logger.debug(f"failed to list keys: {e}")
                continue
        return sorted(all_keys)
    
    def set(self, key: str, value: str) -> None:
        """set in first writable provider"""
        for provider in self.providers:
            try:
                provider.set(key, value)
                logger.debug(f"set secret '{key}' in {provider.__class__.__name__}")
                return
            except NotImplementedError:
                continue
            except Exception as e:
                logger.warning(f"failed to set in {provider.__class__.__name__}: {e}")
                continue
        
        raise NotImplementedError("no writable providers in chain")
