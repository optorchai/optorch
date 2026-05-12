from optorch.llm.projections.registry import CostProjectorRegistry
from optorch.llm.projections.simple_estimator import SimpleCostProjector

CostProjectorRegistry.register("simple", SimpleCostProjector, is_default=True)
