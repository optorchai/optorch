"""Manage per-tenant SCIM tokens"""

import secrets
from datetime import datetime, UTC
from typing import TYPE_CHECKING
from optorch.errors import AuthenticationError

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager


class SCIMTokenManager:
    """Manage per-tenant SCIM tokens"""

    def __init__(self, storage: "StorageManager"):
        self.storage = storage

    async def generate_token(self, organization_id: str) -> str:
        """Generate SCIM token for organization"""
        token = f"scim_{secrets.token_urlsafe(32)}"
        await self.storage.execute("identity.create_scim_token", {"token": token, "organization_id": organization_id, "created_at": datetime.now(UTC)})
        return token

    async def validate_token(self, token: str) -> str:
        """Validate SCIM token, return organization_id"""
        token_data = await self.storage.query("identity.get_scim_token", token=token)
        if not token_data:
            raise AuthenticationError("Invalid SCIM token", details={"token_prefix": token[:10] if token else None})

        return token_data["organization_id"]

    async def revoke_token(self, token: str):
        """Revoke SCIM token"""
        await self.storage.execute("identity.delete_scim_token", {"token": token})
