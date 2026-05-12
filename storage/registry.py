from typing import Dict, Type, Optional
from optorch.storage.store.base import AbstractStore
from optorch.logging import get_logger

logger = get_logger(__name__)


class StorageRegistry:
    """registry for storage backend adapters"""
    
    def __init__(self):
        self._stores: Dict[str, Type[AbstractStore]] = {}
        self._discover_stores()
    
    def _discover_stores(self) -> None:
        """auto-discover store classes from optorch.storage.store package"""
        from optorch.storage.store import TimescaleStore, SqliteStore, MySQLStore
        
        # register built-in stores
        self.register("timescale", TimescaleStore)
        self.register("sqlite", SqliteStore)
        self.register("mysql", MySQLStore)
        
        logger.info(f"discovered {len(self._stores)} storage backends")
    
    def register(self, store_type: str, store_class: Type[AbstractStore]) -> None:
        """register storage backend"""
        if not issubclass(store_class, AbstractStore):
            raise ValueError(f"{store_class.__name__} must extend AbstractStore")
        
        self._stores[store_type] = store_class
        logger.debug(f"registered storage backend: {store_type} -> {store_class.__name__}")
    
    def get(self, store_type: str) -> Type[AbstractStore]:
        """get storage backend class"""
        if store_type not in self._stores:
            raise ValueError(f"unknown storage backend: {store_type}")
        return self._stores[store_type]
    
    def has(self, store_type: str) -> bool:
        """check if storage backend registered"""
        return store_type in self._stores
    
    def list_stores(self) -> list[str]:
        """list all registered storage backends"""
        return list(self._stores.keys())
