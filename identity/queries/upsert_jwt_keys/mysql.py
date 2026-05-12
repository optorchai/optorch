"""upsert JWT keys - mysql"""

from datetime import datetime
from optorch.storage.queries.base import BaseQuery


class UpsertJwtKeysQuery(BaseQuery):
    """update or insert JWT key rotation state"""

    @property
    def query_name(self) -> str:
        return "identity.upsert_jwt_keys"

    async def execute(self, keys_json: str, updated_at: datetime) -> None:
        query = """
            INSERT INTO jwt_keys (id, keys_json, updated_at)
            VALUES (1, :keys_json, :updated_at)
            ON DUPLICATE KEY UPDATE
                keys_json = VALUES(keys_json),
                updated_at = VALUES(updated_at)
        """
        await self.store.execute(query, {"keys_json": keys_json, "updated_at": updated_at})
