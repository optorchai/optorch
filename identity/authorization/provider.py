"""Authorization provider protocol"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from optorch.identity.authorization.models import Decision


class AuthorizationProvider(ABC):
    """XACML-aligned authorization provider interface"""

    @abstractmethod
    async def check_permission(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        environment: Dict[str, Any] | None = None,
    ) -> Decision:
        """Evaluate authorization request (PDP)

        Args:
            subject: User attributes
                {"user_id": "alice", "roles": ["analyst"], "org_id": "acme"}
            resource: Resource attributes
                {"type": "workflow", "id": "tariff_calc", "owner": "bob"}
            action: Action to perform ("execute", "read", "update", "delete")
            environment: Context attributes
                {"time": datetime.now(), "ip": "192.168.1.1"}

        Returns:
            Decision with result ("Permit" | "Deny" | "NotApplicable" | "Indeterminate")
        """
        pass

    @abstractmethod
    async def add_policy(self, policy: Dict[str, Any]) -> None:
        """Add policy to PAP (Policy Administration Point)"""
        pass

    @abstractmethod
    async def remove_policy(self, policy_id: str) -> None:
        """Remove policy from PAP"""
        pass

    @abstractmethod
    async def list_policies(self) -> list[Dict[str, Any]]:
        """List all policies"""
        pass

    @abstractmethod
    async def list_roles(self) -> list[str]:
        """List all available roles"""
        pass

    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass
