from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, TYPE_CHECKING
from databases import Database

if TYPE_CHECKING:
    from optorch.storage.config import StorageConfig


class AbstractStore(ABC):
    """base class for storage backends"""
    
    def __init__(self, config: "StorageConfig"):
        self.config = config
        self.connection_string = config.connection_string
        self.pool_size = config.pool_size
        self.pool_timeout = config.pool_timeout
        self.db: Optional[Database] = None
    
    @abstractmethod
    async def connect(self) -> None:
        """establish database connection"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """close database connection"""
        pass
    
    @abstractmethod
    async def prepare(self) -> None:
        """prepare database - migrations, hypertables, indexes, etc"""
        pass
    
    @abstractmethod
    async def execute(self, query: str, values: Optional[Dict[str, Any]] = None) -> None:
        """execute write query"""
        pass
    
    @abstractmethod
    async def transaction(self):
        """context manager for transactions"""
        pass
    
    # read operations
    @abstractmethod
    async def fetch_one(self, query: str, values: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """fetch single row as dict"""
        pass
    
    @abstractmethod
    async def fetch_all(self, query: str, values: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """fetch all rows as list of dicts"""
        pass
    
    @abstractmethod
    async def fetch_val(self, query: str, values: Optional[Dict[str, Any]] = None, column: int = 0) -> Any:
        """fetch single scalar value"""
        pass
    
    @property
    @abstractmethod
    def store_type(self) -> str:
        """return store type identifier"""
        pass
    
    @abstractmethod
    async def create_migrations_table(self) -> None:
        """create schema_migrations tracking table"""
        pass
    
    @abstractmethod
    async def get_applied_migrations(self) -> set[str]:
        """get set of already applied migration names"""
        pass
    
    @abstractmethod
    async def record_migration(self, migration_name: str) -> None:
        """record that a migration has been applied"""
        pass
    
    async def run_migrations(self) -> None:
        """run database migrations"""
        from pathlib import Path
        from optorch.storage.migrations import MigrationRunner
        import os
        
        if self.config.migrations_path:
            migrations_path = Path(self.config.migrations_path)
        else:
            storage_pkg = os.path.dirname(os.path.dirname(__file__))
            migrations_path = Path(storage_pkg) / "migrations"
        
        runner = MigrationRunner(self, migrations_path)
        await runner.run()
