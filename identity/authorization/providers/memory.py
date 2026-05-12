"""Memory-based authorization provider for testing"""

from typing import Any, Optional, TYPE_CHECKING
from optorch.identity.authorization.provider import AuthorizationProvider
from optorch.identity.authorization.models import Decision
from optorch.logging import get_logger
from optorch.errors import ConfigurationError

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = get_logger(__name__)


class MemoryProvider(AuthorizationProvider):
    """in-memory authorization provider for testing/development
    
    simple rule-based permissions without external dependencies
    """

    def __init__(
        self,
        config: dict,
        storage_manager: Optional["StorageManager"] = None,
    ):
        self.config = config
        self.storage = storage_manager
        
        self.policies: dict[str, list[dict]] = {
            "admin": [{"resource": "*", "action": "*"}],
            "user": [
                {"resource": "workflow", "action": "execute"},
                {"resource": "data", "action": "read"}
            ],
            "viewer": [{"resource": "*", "action": "read"}]
        }

    async def check_permission(
        self,
        subject: dict[str, Any],
        resource: dict[str, Any],
        action: str,
        environment: Optional[dict[str, Any]] = None,
    ) -> Decision:
        """check permission against in-memory policies
        
        matches roles to policies - simple wildcard support
        """
        roles = subject.get("roles", [])
        resource_type = resource.get("type", "*")
        
        for role in roles:
            if role not in self.policies:
                continue
            
            for policy in self.policies[role]:
                if self._matches(policy["resource"], resource_type) and \
                   self._matches(policy["action"], action):
                    return Decision(
                        result="Permit",
                        reason=f"role '{role}' has permission"
                    )
        
        return Decision(result="Deny", reason="no matching policy found")

    async def add_policy(self, policy: dict[str, Any]) -> None:
        """add policy to role"""
        role = policy.get("role")
        if not role:
            raise ConfigurationError("policy must have 'role' key")
        if role not in self.policies:
            self.policies[role] = []
        self.policies[role].append({"resource": policy["resource"], "action": policy["action"]})
        logger.debug(f"added policy for role {role}")

    async def remove_policy(self, policy_id: str) -> None:
        """remove policy by id - noop for simple memory provider"""
        logger.debug(f"remove policy {policy_id} - not implemented")

    async def list_policies(self) -> list[dict[str, Any]]:
        """list all policies"""
        result = []
        for role, policies in self.policies.items():
            for p in policies:
                result.append({"role": role, "resource": p["resource"], "action": p["action"]})
        return result

    async def list_roles(self) -> list[str]:
        """list all available roles from database"""
        if self.storage:
            try:
                return await self.storage.query("identity.list_roles")
            except Exception as e:
                logger.warning(f"failed to query roles from database: {e}")
        
        return list(self.policies.keys())

    def name(self) -> str:
        """provider name"""
        return "memory"

    def _matches(self, pattern: str, value: str) -> bool:
        """simple wildcard matching"""
        if pattern == "*":
            return True
        if pattern == value:
            return True
        if pattern.endswith("*") and value.startswith(pattern[:-1]):
            return True
        return False
