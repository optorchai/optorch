import os
import asyncio
from pathlib import Path
from typing import Optional, Union
from optorch.storage.store.base import AbstractStore
from optorch.logging import get_logger

logger = get_logger(__name__)


class MigrationRunner:
    """database migration runner - reads .sql files and executes in order"""
    
    def __init__(self, store: AbstractStore, migrations_base_path: Optional[Union[str, Path]] = None):
        self.store = store
        self.migrations_base_path = Path(migrations_base_path or "migrations")
        self.migrations_path = self.migrations_base_path / store.store_type
    
    async def run(self) -> None:
        """run all pending migrations"""
        if not self.migrations_path.exists():
            logger.warning(f"migrations path not found: {self.migrations_path}")
            return
        
        # ensure migrations tracking table exists
        await self.store.create_migrations_table()
        
        # get all .sql files in migrations directory
        migration_files = sorted(self.migrations_path.glob("*.sql"))
        
        if not migration_files:
            logger.info("no migrations found")
            return
        
        applied = await self.store.get_applied_migrations()        
        pending = [f for f in migration_files if f.name not in applied]
        
        if not pending:
            logger.info(f"all {len(migration_files)} migrations already applied")
            return
        
        logger.info(f"running {len(pending)} pending migrations from {self.migrations_path}")
        
        for migration_file in pending:
            await self._run_migration(migration_file)
            await self.store.record_migration(migration_file.name)
        
        logger.info(f"migrations complete ({len(pending)} applied)")
    
    async def _run_migration(self, migration_file: Path) -> None:
        """run single migration file"""
        logger.info(f"running migration: {migration_file.name}")
        
        sql = migration_file.read_text()
        statements = self._split_sql_statements(sql)
        
        for statement in statements:
            try:
                await self.store.execute(statement)
            except Exception as e:
                logger.error(f"migration failed: {migration_file.name} - {e}")
                raise
        
        logger.debug(f"migration complete: {migration_file.name}")
    
    def _split_sql_statements(self, sql: str) -> list[str]:
        """split SQL into statements, respecting $$ delimiters, BEGIN/END blocks, and comments"""
        statements = []
        current_statement = []
        in_dollar_quote = False
        in_trigger_block = False
        
        lines = sql.split('\n')
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped or stripped.startswith('--'):
                continue
            
            if '$$' in line:
                in_dollar_quote = not in_dollar_quote
            
            upper_stripped = stripped.upper()
            
            if 'CREATE TRIGGER' in upper_stripped or 'CREATE OR REPLACE TRIGGER' in upper_stripped:
                in_trigger_block = True
            
            current_statement.append(line)
            
            if in_trigger_block and upper_stripped.startswith('END'):
                in_trigger_block = False
            
            if ';' in line and not in_dollar_quote and not in_trigger_block:
                stmt = '\n'.join(current_statement).strip()
                if stmt:
                    statements.append(stmt)
                current_statement = []
        
        if current_statement:
            stmt = '\n'.join(current_statement).strip()
            if stmt:
                statements.append(stmt)
        
        return statements
