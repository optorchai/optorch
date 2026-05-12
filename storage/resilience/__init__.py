"""Resilience strategies for database operations"""
from optorch.storage.resilience.base import ResilienceStrategy
from optorch.storage.resilience.registry import ResilienceRegistry

__all__ = ["ResilienceStrategy", "ResilienceRegistry"]
