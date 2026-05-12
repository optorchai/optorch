"""secret providers init"""

from optorch.config.secrets.providers.environment import EnvironmentSecretProvider
from optorch.config.secrets.providers.dict import DictSecretProvider
from optorch.config.secrets.providers.composite import CompositeSecretProvider

__all__ = [
    "EnvironmentSecretProvider",
    "DictSecretProvider",
    "CompositeSecretProvider",
]
