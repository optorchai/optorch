"""Distribution strategies package"""
from optorch.events.distribution.distribution_strategy import DistributionStrategy
from optorch.events.distribution.tag_based_strategy import TagBasedStrategy

__all__ = ["DistributionStrategy", "TagBasedStrategy"]
