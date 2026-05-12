"""failed login tracker - account lockout"""

import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = logging.getLogger(__name__)


class FailedLoginTracker:
    """track failed login attempts and enforce account lockout
    
    features:
    - attempt counter per user
    - automatic lockout after threshold
    - time-based unlock
    - storage persistence
    """

    def __init__(
        self,
        storage_manager: "StorageManager",
        max_attempts: int = 5,
        lockout_duration: int = 900,  # 15 minutes
        attempt_window: int = 300  # 5 minutes
    ):
        self.storage = storage_manager
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration
        self.attempt_window = attempt_window
    
    async def record_failure(self, user_id: str, reason: str = "invalid_credentials") -> None:
        """record failed login attempt"""
        
        await self.storage.query("identity.create_failed_login_attempt", user_id=user_id, reason=reason)
        recent_attempts = await self.get_recent_attempts(user_id)
        
        if recent_attempts >= self.max_attempts:
            await self._lock_account(user_id)
            logger.warning(f"account locked due to failed login attempts: {user_id}")
    
    async def record_success(self, user_id: str) -> None:
        """reset failed attempt counter on successful login"""
        await self.storage.query("identity.clear_failed_login_attempts", user_id=user_id)
    
    async def is_locked(self, user_id: str) -> bool:
        """check if account is locked"""
        lockout = await self.storage.query(
            "identity.get_account_lockout",
            user_id=user_id
        )
        
        if not lockout:
            return False
        
        if lockout["locked_until"] < datetime.now(UTC):
            await self._unlock_account(user_id)
            return False
        
        return True
    
    async def get_recent_attempts(self, user_id: str) -> int:
        """count failed attempts in time window"""
        cutoff = datetime.now(UTC) - timedelta(seconds=self.attempt_window)
        count = await self.storage.query("identity.count_failed_login_attempts", user_id=user_id, since=cutoff)
        return count
    
    async def _lock_account(self, user_id: str) -> None:
        """lock account for duration"""
        locked_until = datetime.now(UTC) + timedelta(seconds=self.lockout_duration)
        
        await self.storage.query(
            "identity.create_account_lockout",
            user_id=user_id,
            locked_until=locked_until,
            reason="max_failed_attempts"
        )
    
    async def _unlock_account(self, user_id: str) -> None:
        """manually unlock account"""
        await self.storage.query("identity.delete_account_lockout", user_id=user_id)
        logger.info(f"account unlocked: {user_id}")
    
    async def force_unlock(self, user_id: str) -> None:
        """admin unlock account"""
        await self._unlock_account(user_id)
        await self.record_success(user_id)
