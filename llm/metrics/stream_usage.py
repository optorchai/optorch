"""Streaming usage marker class"""
from dataclasses import dataclass

@dataclass
class UsageData:
    """Marker class to pass usage data through stream"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float = 0.0
    currency: str = 'usd'
