"""policy version manager - snapshots and rollback"""

import json
import logging
from datetime import datetime, UTC
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = logging.getLogger(__name__)


class PolicyVersionManager:
    """manage policy snapshots with rollback capability"""

    def __init__(self, storage_manager: "StorageManager"):
        self.storage = storage_manager

    async def create_snapshot(self, description: str = "") -> str:
        """snapshot current policies"""
        policies = await self.storage.query("identity.list_policies")
        snapshot_id = f"snapshot_{datetime.now(UTC).isoformat()}"
        policies_json = json.dumps(policies)
        
        await self.storage.query(
            "identity.create_policy_snapshot",
            snapshot_id=snapshot_id,
            policies=policies_json,
            description=description
        )
        
        logger.info(f"created policy snapshot: {snapshot_id}")
        return snapshot_id

    async def list_snapshots(self) -> List[Dict[str, Any]]:
        """get all policy snapshots"""
        return await self.storage.query("identity.list_policy_snapshots")

    async def restore_snapshot(self, snapshot_id: str) -> None:
        """rollback policies to snapshot"""
        snapshot = await self.storage.query(
            "identity.get_policy_snapshot",
            snapshot_id=snapshot_id
        )
        
        if not snapshot:
            logger.error(f"snapshot not found: {snapshot_id}")
            return
        
        policies = json.loads(snapshot["policies"])
        
        await self.storage.query("identity.delete_all_policies")
        
        for policy in policies:
            await self.storage.query(
                "identity.create_policy",
                subject=policy["subject"],
                resource=policy["resource"],
                action=policy["action"],
                effect=policy.get("effect", "allow")
            )
        
        logger.info(f"restored policy snapshot: {snapshot_id}")

    async def get_snapshot_diff(self, snapshot_id: str) -> Dict[str, Any]:
        """compare current policies to snapshot"""
        snapshot = await self.storage.query(
            "identity.get_policy_snapshot",
            snapshot_id=snapshot_id
        )
        
        if not snapshot:
            logger.error(f"snapshot not found: {snapshot_id}")
            return {"snapshot_id": snapshot_id, "added": [], "removed": [], "unchanged_count": 0}
        
        snapshot_policies = set(
            (p["subject"], p["resource"], p["action"], p.get("effect", "allow"))
            for p in json.loads(snapshot["policies"])
        )
        
        current_policies = set(
            (p["subject"], p["resource"], p["action"], p.get("effect", "allow"))
            for p in await self.storage.query("identity.list_policies")
        )
        
        added = current_policies - snapshot_policies
        removed = snapshot_policies - current_policies
        
        return {
            "snapshot_id": snapshot_id,
            "added": [{"subject": a[0], "resource": a[1], "action": a[2], "effect": a[3]} for a in added],
            "removed": [{"subject": r[0], "resource": r[1], "action": r[2], "effect": r[3]} for r in removed],
            "unchanged_count": len(current_policies & snapshot_policies)
        }

    async def auto_snapshot_before_change(self, description: str = "auto backup") -> Optional[str]:
        """create automatic backup before policy changes"""
        try:
            return await self.create_snapshot(description)
        except Exception as e:
            logger.warning(f"auto snapshot failed: {e}")
            return None
