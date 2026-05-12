"""save JWT key - mysql"""

from datetime import datetime
from optorch.storage.queries.base import BaseQuery


class SaveJwtKeyQuery(BaseQuery):
    """save JWT signing key (for key rotation)"""
    
    @property
    def query_name(self) -> str:
        return "identity.save_jwt_key"
    
    async def execute(self, keys_json: str, updated_at: datetime) -> None:
        # MySQL UPSERT using ON DUPLICATE KEY UPDATE
        query = """
            INSERT INTO jwt_keys (id, keys_json, updated_at)
            VALUES (1, :keys_json, :updated_at)
            ON DUPLICATE KEY UPDATE
                keys_json = VALUES(keys_json),
                updated_at = VALUES(updated_at)
        """
        await self.store.execute(query, {
            "keys_json": keys_json,
            "updated_at": updated_at.isoformat() if hasattr(updated_at, 'isoformat') else updated_at
        })
