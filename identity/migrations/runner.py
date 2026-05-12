"""Migration runner for identity database schemas"""

from pathlib import Path
from typing import TYPE_CHECKING
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = get_logger(__name__)


class MigrationRunner:
    """runs SQL migration files using store's built-in migration system"""
    
    def __init__(self, storage_manager: "StorageManager", migration_dir: Path):
        self.storage = storage_manager
        self.migration_dir = migration_dir
    
    async def run_migrations(self) -> None:
        """execute all pending migrations using store's migration infrastructure"""
        
        if not self.migration_dir.exists():
            logger.warning(f"migration directory does not exist: {self.migration_dir}")
            return
        
        await self.storage._ensure_initialized()
        
        if not self.storage.store:
            raise RuntimeError("storage store not initialized")
        
        store = self.storage.store
        
        await store.create_migrations_table()
        applied = await store.get_applied_migrations()
        
        migration_files = sorted(self.migration_dir.glob("*.sql"))
        
        if not migration_files:
            logger.info("no migration files found")
            return
        
        executed_count = 0
        
        for migration_file in migration_files:
            migration_name = migration_file.stem
            
            if migration_name in applied:
                logger.debug(f"migration already applied: {migration_name}")
                continue
            
            logger.info(f"applying migration: {migration_name}")
            
            try:
                sql = migration_file.read_text()
                statements = self._split_sql_statements(sql)
                
                for statement in statements:
                    if statement:
                        await store.execute(statement)
                
                await store.record_migration(migration_name)
                executed_count += 1
                logger.info(f"migration applied: {migration_name}")
                
            except Exception as e:
                logger.error(f"migration failed: {migration_name} - {e}")
                raise RuntimeError(f"Migration {migration_name} failed: {e}")
        
        if executed_count > 0:
            logger.info(f"applied {executed_count} migrations")
        else:
            logger.info("all migrations up to date")
    
    def _split_sql_statements(self, sql: str) -> list[str]:
        """split SQL by semicolons handling comments"""
        import re
        
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        lines = []
        for line in sql.split('\n'):
            if '--' in line:
                line = line[:line.index('--')]
            lines.append(line)
        
        sql = '\n'.join(lines)
        statements = sql.split(';')
        
        return [s.strip() for s in statements if s.strip()]
