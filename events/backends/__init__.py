"""Event backends package"""
from optorch.events.backends.local_backend import LocalBackend
from optorch.events.backends.sse_backend import SSEBackend

__all__ = ["LocalBackend", "SSEBackend"]
