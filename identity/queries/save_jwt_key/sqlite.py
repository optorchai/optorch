"""save JWT key - sqlite"""

from datetime import datetime
from optorch.storage.queries.base import BaseQuery


class SaveJwtKeyQuery(BaseQuery):
    """save JWT signing key (for key rotation)"""
    
    @property
    def query_name(self) -> str:
        return "identity.save_jwt_key"
    
    async def execute(self, keys_json: str, updated_at: datetime) -> None:
        # SQLite doesn't have UPSERT in older versions, so DELETE + INSERT
        await self.store.execute("DELETE FROM jwt_keys", {})
        
        query = """
            INSERT INTO jwt_keys (keys_json, updated_at)
            VALUES (:keys_json, :updated_at)
        """
        await self.store.execute(query, {
            "keys_json": keys_json,
            "updated_at": updated_at.isoformat() if hasattr(updated_at, 'isoformat') else updated_at
        })
