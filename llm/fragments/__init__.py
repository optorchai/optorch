"""Prompt fragments package"""
from optorch.llm.fragments.base import Fragment
from optorch.llm.fragments.registry import FragmentRegistry

__all__ = [
    "Fragment",
    "FragmentRegistry"
]
