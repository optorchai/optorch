"""Environment variable resolution utility"""
import os


def resolve_env_or_value(value: str) -> str:
    """
    resolve value - check if it's an env var name or actual value
    
    if value contains '://' assume it's already resolved (url, connection string, etc)
    otherwise try to get from environment variable
    
    args:
        value: config value that might be an env var name
        
    returns:
        resolved value (from env or original)
        
    examples:
        resolve_env_or_value("postgresql://...") → "postgresql://..." (passthrough)
        resolve_env_or_value("DATABASE_URL") → os.getenv("DATABASE_URL") or "DATABASE_URL"
        resolve_env_or_value("OPENAI_API_KEY") → os.getenv("OPENAI_API_KEY") or "OPENAI_API_KEY"
    """
    if "://" in value:
        return value
    
    env_value = os.getenv(value)
    if env_value:
        return env_value
    
    return value
