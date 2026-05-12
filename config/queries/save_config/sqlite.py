"""save config - sqlite"""

import json
from typing import Any, Dict, Optional
from optorch.storage.queries.base import BaseQuery
from optorch.logging import get_logger

logger = get_logger(__name__)


class SaveConfigQuery(BaseQuery):
    """save or update config with tenant support"""
    
    @property
    def query_name(self) -> str:
        return "save_config"
    
    async def execute(self, namespace: str, config_data: Dict[str, Any], organization_id: Optional[str] = None) -> None:
        query = """
            INSERT INTO optorch_config (namespace, organization_id, config_data, updated_at, is_active)
            VALUES (:namespace, :organization_id, :config_data, datetime('now'), 1)
            ON CONFLICT (namespace, organization_id) DO UPDATE SET
                config_data = excluded.config_data,
                updated_at = datetime('now')
        """
        await self.store.execute(query, {
            "namespace": namespace,
            "organization_id": organization_id,
            "config_data": json.dumps(config_data)
        })
        logger.info(f"saved config: {namespace} (org={organization_id or 'global'})")
