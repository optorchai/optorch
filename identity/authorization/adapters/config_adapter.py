"""Casbin config adapter - dynamic policy loading with hot reload"""

from pydantic import BaseModel, Field
from typing import Any, TYPE_CHECKING, List, Dict
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = get_logger(__name__)


class ConfigAdapterConfig(BaseModel):
    """config adapter configuration"""
    policies: List[Dict[str, str]] = Field(default_factory=list, description="static policies to load")


class ConfigAdapter:
    """Casbin adapter using storage with dynamic loading"""

    def __init__(self, storage_manager: "StorageManager", config: ConfigAdapterConfig):
        self.storage = storage_manager
        self.config = config
        self._policy_cache: List[Dict] = []

    def load_policy(self, model: Any):
        """Load policies from config or storage with hot reload support"""
        try:
            from casbin import persist
        except ImportError:
            logger.warning("Casbin not installed, policy loading skipped")
            return

        policies = self._load_from_storage()
        
        if not policies:
            policies = self.config.policies
        
        self._policy_cache = policies
        
        for policy in policies:
            line = self._policy_to_line(policy)
            persist.load_policy_line(line, model)
        
        logger.info(f"Loaded {len(policies)} policies from {'storage' if self._load_from_storage() else 'config'}")

    def reload_policy(self, model: Any):
        """hot reload policies from source"""
        logger.info("Reloading policies...")
        model.clear_policy()
        self.load_policy(model)

    def save_policy(self, model: Any):
        """Save policies to config and storage"""
        policies = []

        if hasattr(model, "model") and "p" in model.model and "p" in model.model["p"]:
            for ptype, policy in model.model["p"]["p"].policy:
                policies.append({
                    "subject": policy[0],
                    "resource": policy[1],
                    "action": policy[2],
                    "effect": "allow"
                })

        self._policy_cache = policies
        
        if self.storage:
            try:
                self._save_to_storage(policies)
            except Exception as e:
                logger.error(f"Failed to save policies to storage: {e}")
        
        logger.info(f"Saved {len(policies)} policies")

    def add_policy(self, sec: str, ptype: str, rule: list[str]):
        """Add policy dynamically"""
        if sec == "p" and ptype == "p" and len(rule) >= 3:
            policy = {
                "subject": rule[0],
                "resource": rule[1],
                "action": rule[2],
                "effect": "allow"
            }
            self._policy_cache.append(policy)
            
            if self.storage:
                try:
                    self._add_policy_to_storage(policy)
                except Exception as e:
                    logger.error(f"Failed to add policy to storage: {e}")

    def remove_policy(self, sec: str, ptype: str, rule: list[str]):
        """Remove policy dynamically"""
        if sec == "p" and ptype == "p" and len(rule) >= 3:
            policy = {"subject": rule[0], "resource": rule[1], "action": rule[2]}
            self._policy_cache = [p for p in self._policy_cache if not self._policy_matches(p, policy)]
            
            if self.storage:
                try:
                    self._remove_policy_from_storage(policy)
                except Exception as e:
                    logger.error(f"Failed to remove policy from storage: {e}")

    def remove_filtered_policy(
        self, sec: str, ptype: str, field_index: int, *field_values: str
    ):
        """Remove filtered policy"""
        if sec == "p" and ptype == "p":
            self._policy_cache = [
                p for p in self._policy_cache
                if not self._matches_filter(p, field_index, field_values)
            ]

    def _policy_to_line(self, policy: Dict) -> str:
        """convert policy dict to casbin line format"""
        return f"p, {policy['subject']}, {policy['resource']}, {policy['action']}"
    
    def _policy_matches(self, p1: Dict, p2: Dict) -> bool:
        """check if two policies match"""
        return (p1.get("subject") == p2.get("subject") and
                p1.get("resource") == p2.get("resource") and
                p1.get("action") == p2.get("action"))
    
    def _matches_filter(self, policy: Dict, field_index: int, field_values: tuple) -> bool:
        """check if policy matches filter"""
        fields = [policy.get("subject"), policy.get("resource"), policy.get("action")]
        for i, val in enumerate(field_values):
            if field_index + i < len(fields) and fields[field_index + i] != val:
                return False
        return True
    
    def _load_from_storage(self) -> List[Dict]:
        """load policies from storage"""
        if not self.storage:
            return []
        
        try:
            import asyncio
            result = asyncio.create_task(self.storage.query("identity.list_policies"))
            return asyncio.get_event_loop().run_until_complete(result) if result else []
        except Exception as e:
            logger.debug(f"Storage policy load failed: {e}")
            return []
    
    async def _save_to_storage_async(self, policies: List[Dict]):
        """save all policies to storage"""
        if not self.storage:
            return
        
        await self.storage.query("identity.delete_all_policies")
        
        for policy in policies:
            await self.storage.query("identity.create_policy", **policy)
    
    def _save_to_storage(self, policies: List[Dict]):
        """save all policies to storage (sync wrapper)"""
        import asyncio
        asyncio.create_task(self._save_to_storage_async(policies))
    
    async def _add_policy_to_storage_async(self, policy: Dict):
        """add single policy to storage"""
        if self.storage:
            await self.storage.query("identity.create_policy", **policy)
    
    def _add_policy_to_storage(self, policy: Dict):
        """add single policy to storage (sync wrapper)"""
        import asyncio
        asyncio.create_task(self._add_policy_to_storage_async(policy))
    
    async def _remove_policy_from_storage_async(self, policy: Dict):
        """remove single policy from storage"""
        if self.storage:
            await self.storage.query("identity.delete_policy", **policy)
    
    def _remove_policy_from_storage(self, policy: Dict):
        """remove single policy from storage (sync wrapper)"""
        import asyncio
        asyncio.create_task(self._remove_policy_from_storage_async(policy))

