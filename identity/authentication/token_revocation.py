"""Token revocation service for JWT blacklist"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta, UTC
from optorch.logging import get_logger
import hashlib

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = get_logger(__name__)


class TokenRevocationService:
    """Track revoked tokens using storage backend"""
    
    def __init__(self, storage_manager: Optional["StorageManager"] = None):
        self.storage = storage_manager
    
    async def revoke_token(self, token: str, expires_at: Optional[datetime] = None) -> None:
        """Add token to blacklist
        
        Args:
            token: JWT access or refresh token
            expires_at: When token naturally expires (for cleanup)
        """
        if not self.storage:
            logger.warning("No storage configured - token revocation disabled")
            return
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        if not expires_at:
            expires_at = datetime.now(UTC) + timedelta(hours=1)
        
        try:
            await self.storage.query(
                "identity.revoke_refresh_token",
                token_hash=token_hash,
                expires_at=expires_at.isoformat()
            )
            logger.debug(f"Revoked token: {token_hash[:16]}...")
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
    
    async def is_revoked(self, token: str) -> bool:
        """Check if token is revoked
        
        Args:
            token: JWT token to check
            
        Returns:
            True if token is in blacklist
        """
        if not self.storage:
            return False
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        try:
            result = await self.storage.query(
                "identity.check_revoked_token",
                token_hash=token_hash
            )
            return result is not None and result.get("status") == "revoked"
        except Exception:
            return False
    
    async def cleanup_expired(self, cutoff_hours: int = 24) -> int:
        """Remove expired tokens from blacklist
        
        Args:
            cutoff_hours: Remove tokens older than this
            
        Returns:
            Number of tokens removed
        """
        if not self.storage:
            return 0
        
        cutoff = datetime.now(UTC) - timedelta(hours=cutoff_hours)
        
        try:
            result = await self.storage.query(
                "identity.cleanup_revoked_tokens",
                cutoff=cutoff
            )
            count = result.get("deleted", 0) if result else 0
            logger.info(f"Cleaned up {count} expired revoked tokens")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup revoked tokens: {e}")
            return 0
