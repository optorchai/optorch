"""save JWT key - timescale"""

from datetime import datetime
from optorch.storage.queries.base import BaseQuery


class SaveJwtKeyQuery(BaseQuery):
    """save JWT signing key (for key rotation)"""
    
    @property
    def query_name(self) -> str:
        return "identity.save_jwt_key"
    
    async def execute(self, keys_json: str, updated_at: datetime) -> None:
        # PostgreSQL UPSERT - replace the single row
        query = """
            INSERT INTO jwt_keys (id, keys_json, updated_at)
            VALUES (1, :keys_json, :updated_at)
            ON CONFLICT (id) DO UPDATE SET
                keys_json = EXCLUDED.keys_json,
                updated_at = EXCLUDED.updated_at
        """
        await self.store.execute(query, {
            "keys_json": keys_json,
            "updated_at": updated_at.isoformat() if hasattr(updated_at, 'isoformat') else updated_at
        })
