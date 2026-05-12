from typing import Any, Dict, List, Optional
from pathlib import Path
from databases import Database
from .base import AbstractStore
from optorch.logging import get_logger

logger = get_logger(__name__)


class SqliteStore(AbstractStore):
    """sqlite storage backend"""
    
    async def connect(self) -> None:
        """establish database connection"""
        if "sqlite:///" in self.connection_string:
            db_path = self.connection_string.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"ensured sqlite directory exists: {Path(db_path).parent}")
        
        self.db = Database(self.connection_string)
        await self.db.connect()
        logger.info(f"sqlite connected: {self.connection_string}")
    
    async def disconnect(self) -> None:
        """close database connection"""
        if self.db:
            await self.db.disconnect()
            logger.info("sqlite disconnected")
    
    async def prepare(self) -> None:
        """prepare sqlite - enable foreign keys, wal mode, etc"""
        # sqlite-specific optimizations
        if self.db:
            await self.db.execute("PRAGMA foreign_keys = ON")
            await self.db.execute("PRAGMA journal_mode = WAL")
        logger.info("sqlite prepare complete")
    
    async def execute(self, query: str, values: Optional[Dict[str, Any]] = None) -> None:
        """execute write query"""
        if not self.db:
            raise RuntimeError("database not connected")
        await self.db.execute(query=query, values=values or {})
    
    def transaction(self):
        """context manager for transactions"""
        if not self.db:
            raise RuntimeError("database not connected")
        return self.db.transaction()
    
    async def fetch_one(self, query: str, values: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """fetch single row as dict"""
        if not self.db:
            raise RuntimeError("database not connected")
        result = await self.db.fetch_one(query=query, values=values or {})
        return dict(result) if result else None
    
    async def fetch_all(self, query: str, values: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """fetch all rows as list of dicts"""
        if not self.db:
            raise RuntimeError("database not connected")
        results = await self.db.fetch_all(query=query, values=values or {})
        return [dict(row) for row in results]
    
    async def fetch_val(self, query: str, values: Optional[Dict[str, Any]] = None, column: int = 0) -> Any:
        """fetch single scalar value"""
        if not self.db:
            raise RuntimeError("database not connected")
        return await self.db.fetch_val(query=query, values=values or {}, column=column)
    
    @property
    def store_type(self) -> str:
        return "sqlite"
    
    async def create_migrations_table(self) -> None:
        """create migrations tracking table"""
        sql = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT NOT NULL UNIQUE,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        await self.execute(sql)
    
    async def get_applied_migrations(self) -> set[str]:
        """get set of already applied migration names"""
        if not self.db:
            return set()
        try:
            query = "SELECT migration_name FROM schema_migrations"
            result = await self.db.fetch_all(query=query)
            return {row["migration_name"] for row in result}
        except Exception:
            return set()
    
    async def record_migration(self, migration_name: str) -> None:
        """record that a migration has been applied"""
        sql = """
            INSERT OR IGNORE INTO schema_migrations (migration_name) 
            VALUES (:name)
        """
        await self.execute(sql, {"name": migration_name})
