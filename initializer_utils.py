"""common utilities for package initializers"""

from optorch.logging import get_logger
from typing import Dict, Any, Optional
from optorch.config import ConfigManager

logger = get_logger(__name__)


def extract_optorch_config(
    config_manager: ConfigManager,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """extract optorch config dict from config_manager
    
    args:
        config_manager: ConfigManager instance
        config: optional override dict to merge with base config
        
    returns:
        optorch config dict (base merged with overrides)
    """
    from optorch.config.merger import deep_merge
    
    base_config = config_manager.optorch.model_dump()
    
    if config:
        return deep_merge(base_config, config)
    
    return base_config
