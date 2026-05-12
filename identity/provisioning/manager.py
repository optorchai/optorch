"""SCIM provisioning manager"""

from typing import TYPE_CHECKING, Optional

from optorch.errors import AuthenticationError
from optorch.identity.provisioning.mapper import SCIMMapper
from optorch.identity.provisioning.token_manager import SCIMTokenManager

if TYPE_CHECKING:
    from optorch.identity.config import ProvisioningConfig
    from optorch.identity.organization.manager import OrganizationManager
    from optorch.events.event_emitter import EventEmitter
    from optorch.storage.manager import StorageManager


class SCIMManager:
    """Manages SCIM provisioning"""

    def __init__(
        self,
        config: "ProvisioningConfig",
        org_manager: "OrganizationManager",
        event_emitter: Optional["EventEmitter"] = None
    ):
        self.config = config
        self.org_manager = org_manager
        self.event_emitter = event_emitter
        self.mapper = SCIMMapper(role_mapping=config.role_mapping)
        self.token_manager = SCIMTokenManager(org_manager.storage)
        self.storage: "StorageManager" = org_manager.storage

    async def validate_token(self, authorization: str) -> str:
        """Extract and validate bearer token, return org_id"""
        if not authorization.startswith("Bearer "):
            raise AuthenticationError("Invalid authorization header", details={"authorization_prefix": authorization[:20] if authorization else None})

        token = authorization.replace("Bearer ", "")
        return await self.token_manager.validate_token(token)
