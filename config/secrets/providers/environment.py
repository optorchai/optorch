"""environment secret provider - default secrets from os.environ"""

import os
from typing import Optional, Dict, List, Set
from optorch.logging import get_logger

logger = get_logger(__name__)


class EnvironmentSecretProvider:
    """read secrets from environment variables - tracks .env file keys separately"""
    
    def __init__(self):
        """initialize and load .env file keys"""
        self._dotenv_keys: Set[str] = set()
        self._load_dotenv_keys()
    
    def _load_dotenv_keys(self) -> None:
        """load keys from .env file if it exists"""
        dotenv_path = os.path.join(os.getcwd(), '.env')
        if not os.path.exists(dotenv_path):
            logger.debug(".env file not found - list_keys will return all env vars")
            return
        
        try:
            with open(dotenv_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key = line.split('=', 1)[0].strip()
                        self._dotenv_keys.add(key)
            logger.debug(f"loaded {len(self._dotenv_keys)} keys from .env file")
        except Exception as e:
            logger.warning(f"failed to read .env file: {e}")
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """get secret from environment
        
        args:
            key: environment variable name
            default: fallback value
        
        returns:
            secret value or default
        """
        value = os.getenv(key, default)
        if value is None:
            logger.debug(f"secret not found: {key}")
        return value
    
    def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """batch get from environment"""
        return {key: os.getenv(key) for key in keys}
    
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """list keys from .env file (or all env vars if .env not found)
        
        returns only keys defined in .env file, not system environment variables
        """
        # use .env keys if available, otherwise fall back to all env vars
        keys = list(self._dotenv_keys) if self._dotenv_keys else list(os.environ.keys())
        
        if prefix:
            return [k for k in keys if k.startswith(prefix)]
        
        return keys
    
    def set(self, key: str, value: str) -> None:
        """set environment variable and persist to .env file
        
        args:
            key: environment variable name
            value: secret value
        """
        os.environ[key] = value
        self._dotenv_keys.add(key)
        
        dotenv_path = os.path.join(os.getcwd(), '.env')
        
        existing_lines = []
        key_found = False
        
        if os.path.exists(dotenv_path):
            try:
                with open(dotenv_path, 'r') as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#') and '=' in stripped:
                            existing_key = stripped.split('=', 1)[0].strip()
                            if existing_key == key:
                                existing_lines.append(f"{key}={value}\n")
                                key_found = True
                            else:
                                existing_lines.append(line)
                        else:
                            existing_lines.append(line)
            except Exception as e:
                logger.warning(f"failed to read .env file: {e}")
        
        if not key_found:
            existing_lines.append(f"{key}={value}\n")
        
        try:
            with open(dotenv_path, 'w') as f:
                f.writelines(existing_lines)
            logger.debug(f"persisted secret to .env: {key}")
        except Exception as e:
            logger.error(f"failed to write .env file: {e}")
            raise
    
    def delete(self, key: str) -> None:
        """delete environment variable and remove from .env file
        
        args:
            key: environment variable name to delete
        """
        if key in os.environ:
            del os.environ[key]
        self._dotenv_keys.discard(key)
        
        dotenv_path = os.path.join(os.getcwd(), '.env')
        
        if os.path.exists(dotenv_path):
            try:
                filtered_lines = []
                with open(dotenv_path, 'r') as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped and not stripped.startswith('#') and '=' in stripped:
                            existing_key = stripped.split('=', 1)[0].strip()
                            if existing_key != key:
                                filtered_lines.append(line)
                        else:
                            filtered_lines.append(line)
                
                with open(dotenv_path, 'w') as f:
                    f.writelines(filtered_lines)
                logger.debug(f"deleted secret from .env: {key}")
            except Exception as e:
                logger.error(f"failed to update .env file: {e}")
                raise
        else:
            logger.debug(f"deleted environment variable: {key}")
