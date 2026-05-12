"""JWT key rotation manager - handles secret versioning and rollover"""

from typing import Dict, Optional, List, Any, TYPE_CHECKING
from datetime import datetime, timedelta, UTC
from optorch.errors import ConfigurationError
from optorch.logging import get_logger
import secrets
import json
import asyncio

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = get_logger(__name__)


class KeyRotationManager:
    """manages JWT signing key rotation with backward compatibility"""
    
    def __init__(
        self,
        storage_manager: Optional["StorageManager"] = None,
        rotation_days: int = 90,
        grace_period_days: int = 7,
        enable_auto_rotation: bool = True,
        check_interval_hours: int = 24
    ):
        self.storage = storage_manager
        self.rotation_days = rotation_days
        self.grace_period_days = grace_period_days
        self.enable_auto_rotation = enable_auto_rotation
        self.check_interval_hours = check_interval_hours
        self._keys_cache: Dict[str, Dict] = {}
        self._rotation_task: Optional[asyncio.Task] = None
        self._should_stop = False
    
    async def get_current_key(self) -> Dict[str, Any]:
        """get current active signing key"""
        keys = await self._load_keys()
        
        current = keys.get("current")
        if not current:
            return await self.rotate_key()
        
        issued_at = datetime.fromisoformat(current["issued_at"])
        age = (datetime.now(UTC) - issued_at).days
        
        if age >= self.rotation_days:
            logger.info(f"Key age ({age} days) exceeds rotation period ({self.rotation_days}), rotating...")
            return await self.rotate_key()
        
        return current
    
    async def rotate_key(self) -> Dict[str, Any]:
        """rotate to new signing key, archive old key"""
        keys = await self._load_keys()
        
        new_key = {
            "kid": secrets.token_urlsafe(16),
            "secret": secrets.token_urlsafe(64),
            "algorithm": "HS256",
            "issued_at": datetime.now(UTC).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(days=self.rotation_days + self.grace_period_days)).isoformat()
        }
        
        if keys.get("current"):
            if "archived" not in keys:
                keys["archived"] = []
            keys["archived"].append(keys["current"])
        
        keys["current"] = new_key
        
        keys["archived"] = [
            k for k in keys.get("archived", [])
            if datetime.fromisoformat(k["expires_at"]) > datetime.now(UTC)
        ]
        
        await self._save_keys(keys)
        
        logger.info(f"Rotated JWT signing key: kid={new_key['kid']}")
        return new_key
    
    async def get_verification_keys(self) -> List[Dict[str, Any]]:
        """get all valid keys for verification (current + archived in grace period)"""
        keys = await self._load_keys()
        
        valid_keys = []
        
        if keys.get("current"):
            valid_keys.append(keys["current"])
        
        for archived in keys.get("archived", []):
            expires_at = datetime.fromisoformat(archived["expires_at"])
            if expires_at > datetime.now(UTC):
                valid_keys.append(archived)
        
        return valid_keys
    
    async def get_key_by_kid(self, kid: str) -> Optional[Dict[str, Any]]:
        """lookup key by kid from current or archived keys"""
        keys = await self._load_keys()
        
        if keys.get("current") and keys["current"].get("kid") == kid:
            return keys["current"]
        
        for archived in keys.get("archived", []):
            if archived.get("kid") == kid:
                expires_at = datetime.fromisoformat(archived["expires_at"])
                if expires_at > datetime.now(UTC):
                    return archived
        
        logger.warning(f"Key with kid={kid} not found in current or archived keys")
        return None
    
    async def _load_keys(self) -> Dict:
        """load keys from storage or cache"""
        if self._keys_cache:
            return self._keys_cache
        
        if not self.storage:
            return {}
        
        try:
            result = await self.storage.query("identity.get_jwt_keys")
            if result:
                self._keys_cache = json.loads(result["keys_json"])
                return self._keys_cache
        except Exception as e:
            logger.warning(f"Failed to load keys from storage: {e}")
        
        return {}
    
    async def _save_keys(self, keys: Dict) -> None:
        """persist keys to storage"""
        self._keys_cache = keys
        
        if not self.storage:
            return
        
        try:
            await self.storage.query("identity.save_jwt_key", keys_json=json.dumps(keys), updated_at=datetime.now(UTC))
        except Exception as e:
            logger.error(f"Failed to save keys to storage: {e}")
            raise ConfigurationError("Key rotation failed - storage unavailable")
    
    def start_rotation_task(self) -> None:
        """start background key rotation task"""
        if not self.enable_auto_rotation:
            logger.info("Automatic key rotation disabled")
            return
        
        if self._rotation_task and not self._rotation_task.done():
            logger.warning("Rotation task already running")
            return
        
        self._should_stop = False
        self._rotation_task = asyncio.create_task(self._rotation_loop())
        logger.info(f"Started key rotation task (interval: {self.check_interval_hours}h)")
    
    async def stop_rotation_task(self) -> None:
        """stop background key rotation task"""
        if not self._rotation_task:
            return
        
        self._should_stop = True
        
        if not self._rotation_task.done():
            try:
                await asyncio.wait_for(self._rotation_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._rotation_task.cancel()
                try:
                    await self._rotation_task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Stopped key rotation task")
    
    async def _rotation_loop(self) -> None:
        """background loop for key rotation checks"""
        while not self._should_stop:
            try:
                await self.get_current_key()
                
            except Exception as e:
                logger.error(f"Key rotation check failed: {e}")
            
            check_interval_seconds = int(self.check_interval_hours * 3600)
            
            for _ in range(check_interval_seconds):
                if self._should_stop:
                    break
                await asyncio.sleep(1)
    
    async def cleanup(self) -> None:
        """cleanup resources"""
        await self.stop_rotation_task()
