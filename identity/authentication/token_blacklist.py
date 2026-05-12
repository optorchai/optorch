"""Token blacklist manager - revoke JWTs before expiry"""

from typing import Optional, Set, TYPE_CHECKING
from datetime import datetime, timedelta, UTC
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.cache.manager import CacheManager

logger = get_logger(__name__)


class TokenBlacklist:
    """manages revoked tokens with cache and database persistence"""
    
    def __init__(self, storage_manager: Optional["StorageManager"] = None, cache_manager: Optional["CacheManager"] = None):
        self.storage = storage_manager
        self.cache = cache_manager
        self._memory_blacklist: Set[str] = set()  # fallback
    
    async def revoke(self, token_jti: str, expires_at: datetime) -> None:
        """add token to blacklist"""
        if self.cache:
            ttl = int((expires_at - datetime.now(UTC)).total_seconds())
            await self.cache.set(f"blacklist:{token_jti}", "1", ttl=ttl)
        
        if self.storage:
            try:
                await self.storage.query(
                    "identity.create_revoked_token",
                    jti=token_jti,
                    revoked_at=datetime.now(UTC),
                    expires_at=expires_at
                )
            except Exception as e:
                logger.error(f"Failed to persist token revocation: {e}")
        
        self._memory_blacklist.add(token_jti)
        logger.info(f"Token revoked: jti={token_jti}")
    
    async def is_revoked(self, token_jti: str) -> bool:
        """check if token is blacklisted"""
        if self.cache:
            cached = await self.cache.get(f"blacklist:{token_jti}")
            if cached is not None:
                return True
        
        if token_jti in self._memory_blacklist:
            return True
        
        if self.storage:
            try:
                result = await self.storage.query("check_revoked_token", jti=token_jti)
                return result is not None
            except Exception as e:
                logger.warning(f"Blacklist database check failed: {e}")
        
        return False
    
    async def cleanup_expired(self) -> int:
        """remove expired tokens from blacklist, return count cleaned"""
        if not self.storage:
            return 0
        
        try:
            result = await self.storage.query(
                "identity.delete_expired_revoked_tokens",
                cutoff_time=datetime.now(UTC)
            )
            count = result.get("deleted_count", 0) if result else 0
            logger.info(f"Cleaned up {count} expired revoked tokens")
            return count
        except Exception as e:
            logger.error(f"Blacklist cleanup failed: {e}")
            return 0
