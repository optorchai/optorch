"""config providers init"""

from optorch.config.providers.yaml import YamlConfigProvider
from optorch.config.providers.dict import DictConfigProvider

__all__ = [
    "YamlConfigProvider",
    "DictConfigProvider",
]
