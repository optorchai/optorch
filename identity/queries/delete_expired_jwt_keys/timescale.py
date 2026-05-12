"""delete expired JWT keys - timescale"""

from datetime import datetime, UTC
from optorch.storage.queries.base import BaseQuery


class DeleteExpiredJwtKeysQuery(BaseQuery):
    """delete expired JWT signing keys (for key rotation cleanup)"""
    
    @property
    def query_name(self) -> str:
        return "identity.delete_expired_jwt_keys"
    
    async def execute(self) -> int:
        # JWT keys table only stores one row (latest state)
        # Cleanup is handled by save_jwt_key which replaces the row
        # This is just for API compatibility
        return 0
