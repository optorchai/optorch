"""Open Policy Agent (OPA) authorization provider"""

from typing import Any, Optional, TYPE_CHECKING
from optorch.identity.authorization.provider import AuthorizationProvider
from optorch.identity.authorization.models import Decision
from optorch.logging import get_logger
import httpx
import asyncio
from datetime import UTC, datetime, timedelta

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager

logger = get_logger(__name__)


class CircuitBreaker:
    """simple circuit breaker for OPA health"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
    
    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure = datetime.now(UTC)
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"circuit breaker opened after {self.failures} failures")
    
    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"
    
    def can_attempt(self) -> bool:
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if self.last_failure and datetime.now(UTC) - self.last_failure > timedelta(seconds=self.timeout):
                self.state = "half-open"
                logger.info("circuit breaker half-open, attempting recovery")
                return True
            return False
        
        return True  # half-open allows attempts


class OPAProvider(AuthorizationProvider):
    """Open Policy Agent authorization provider with production hardening
    
    Features:
    - retry logic with exponential backoff
    - circuit breaker to fail fast when OPA down
    - timeout handling
    - connection pooling
    """

    def __init__(
        self,
        config: dict,
        storage_manager: Optional["StorageManager"] = None,
    ):
        self.config = config
        self.storage = storage_manager
        
        self.url = config.get("url", "http://localhost:8181")
        self.policy_path = config.get("policy_path", "/v1/data/optorch/authz/allow")
        self.timeout = config.get("timeout", 5.0)
        self.max_retries = config.get("max_retries", 3)
        self.retry_backoff = config.get("retry_backoff", 0.5)
        
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.get("circuit_breaker_threshold", 5),
            timeout=config.get("circuit_breaker_timeout", 60)
        )
        
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        self.client = httpx.AsyncClient(timeout=self.timeout, limits=limits)

    async def check_permission(
        self,
        subject: dict[str, Any],
        resource: dict[str, Any],
        action: str,
        environment: Optional[dict[str, Any]] = None,
    ) -> Decision:
        """check permission via OPA policy evaluation with retry
        
        Args:
            subject: user context (user_id, roles, etc)
            resource: resource being accessed (type, id, etc)
            action: action being performed
            environment: additional context (org_id, time, etc)
        
        Returns:
            Decision with permit/deny
        """
        if not self.circuit_breaker.can_attempt():
            logger.error("circuit breaker open, denying by default")
            return Decision(result="Deny", reason="OPA circuit breaker open")
        
        input_data = {
            "subject": subject,
            "resource": resource,
            "action": action,
            "environment": environment or {}
        }
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.url}{self.policy_path}",
                    json={"input": input_data},
                )
                response.raise_for_status()
                
                result = response.json()
                allowed = result.get("result", False)
                
                self.circuit_breaker.record_success()
                return Decision(
                    result="Permit" if allowed else "Deny",
                    reason=f"OPA policy decision: {'allow' if allowed else 'deny'}"
                )

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"opa timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_backoff * (2 ** attempt))
                    
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.error(f"opa http error {e.response.status_code}: {e}")
                break  # don't retry on 4xx/5xx
                
            except Exception as e:
                last_error = e
                logger.error(f"opa check failed on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_backoff * (2 ** attempt))
        
        self.circuit_breaker.record_failure()
        return Decision(result="Deny", reason=f"OPA evaluation error: {str(last_error)}")
    
    async def add_policy(self, policy: dict[str, Any]) -> None:
        """OPA policies managed externally via bundles/files"""
        logger.warning("add_policy not supported for OPA - manage policies via bundles")
    
    async def remove_policy(self, policy_id: str) -> None:
        """OPA policies managed externally via bundles/files"""
        logger.warning("remove_policy not supported for OPA - manage policies via bundles")
    
    async def list_policies(self) -> list[dict[str, Any]]:
        """OPA policies managed externally via bundles/files"""
        logger.warning("list_policies not supported for OPA - query OPA directly")
        return []
    
    async def list_roles(self) -> list[str]:
        """list all roles from database (roles are stored in org memberships)"""
        if self.storage:
            try:
                return await self.storage.query("identity.list_roles")
            except Exception as e:
                logger.warning(f"failed to query roles from database: {e}")
        
        logger.debug("no storage available, returning empty list")
        return []
    
    def name(self) -> str:
        return "opa"
    
    async def close(self) -> None:
        """cleanup connection pool"""
        await self.client.aclose()
