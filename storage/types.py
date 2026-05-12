"""Storage type definitions"""
from enum import Flag, auto


class StorageRole(Flag):
    """Storage access roles for permission control"""
    READ = auto()
    WRITE = auto()
    READ_WRITE = READ | WRITE


__all__ = ["StorageRole"]
