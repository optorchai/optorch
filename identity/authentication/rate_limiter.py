"""Rate limiting for authentication attempts"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta, UTC
from collections import defaultdict, deque
from optorch.logging import get_logger
from optorch.errors import AuthenticationError
from optorch.identity.authentication.config import RateLimitConfig

logger = get_logger(__name__)


class RateLimitExceeded(AuthenticationError):
    """Raised when rate limit is exceeded"""
    def __init__(self, retry_after_seconds: int, identifier: str):
        super().__init__(
            f"Rate limit exceeded for {identifier}. Retry after {retry_after_seconds}s",
            details={
                "identifier": identifier,
                "retry_after_seconds": retry_after_seconds
            }
        )
        self.retry_after_seconds = retry_after_seconds


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for authentication"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        cfg = config or RateLimitConfig()
        self.max_attempts = cfg.max_attempts
        self.window_seconds = cfg.window_seconds
        self.lockout_duration = cfg.lockout_seconds
        
        self._attempts: Dict[str, deque] = defaultdict(deque)
        self._lockouts: Dict[str, datetime] = {}
    
    async def check_rate_limit(self, identifier: str) -> None:
        """Check if identifier is within rate limits
        
        Args:
            identifier: Email, username, or IP address
            
        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        now = datetime.now(UTC)
        
        if identifier in self._lockouts:
            lockout_until = self._lockouts[identifier]
            if now < lockout_until:
                retry_after = int((lockout_until - now).total_seconds())
                logger.warning(f"authentication attempt blocked for {identifier} (locked out for {retry_after}s)")
                raise RateLimitExceeded(retry_after, identifier)
            else:
                del self._lockouts[identifier]
                self._attempts[identifier].clear()
        
        attempts = self._attempts[identifier]
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        
        if len(attempts) >= self.max_attempts:
            lockout_until = now + timedelta(seconds=self.lockout_duration)
            self._lockouts[identifier] = lockout_until
            
            logger.warning(
                f"rate limit exceeded for {identifier}: "
                f"{len(attempts)} attempts in {self.window_seconds}s, "
                f"locked out until {lockout_until.isoformat()}"
            )
            
            raise RateLimitExceeded(self.lockout_duration, identifier)
    
    async def record_attempt(self, identifier: str, success: bool = False) -> None:
        """Record authentication attempt
        
        Args:
            identifier: Email, username, or IP address
            success: Whether attempt was successful
        """
        now = datetime.now(UTC)
        
        if success:
            if identifier in self._attempts:
                self._attempts[identifier].clear()
            if identifier in self._lockouts:
                del self._lockouts[identifier]
            logger.debug(f"successful login for {identifier}, rate limit reset")
        else:
            self._attempts[identifier].append(now)
            logger.debug(f"failed attempt recorded for {identifier} ({len(self._attempts[identifier])} in window)")
    
    def get_remaining_attempts(self, identifier: str) -> int:
        """Get number of remaining attempts before lockout"""
        now = datetime.now(UTC)
        
        if identifier in self._lockouts and now < self._lockouts[identifier]:
            return 0
        
        attempts = self._attempts[identifier]
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        current_attempts = sum(1 for attempt in attempts if attempt >= cutoff)
        remaining = max(0, self.max_attempts - current_attempts)
        
        return remaining
    
    def reset(self, identifier: str) -> None:
        """Reset rate limit for identifier (admin override)"""
        if identifier in self._attempts:
            del self._attempts[identifier]
        if identifier in self._lockouts:
            del self._lockouts[identifier]
        logger.info(f"rate limit reset for {identifier}")


class RateLimitMiddleware:
    """Middleware for applying rate limits to authentication"""
    
    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        limiter: Optional[SlidingWindowRateLimiter] = None
    ):
        cfg = config or RateLimitConfig()
        self.limiter = limiter or SlidingWindowRateLimiter(config=cfg)
        self.identify_by = cfg.identify_by
    
    def _get_identifier(self, request: Any, credentials: Optional[dict] = None) -> str:
        """Extract identifier from request"""
        identifiers = []
        
        if self.identify_by in ("email", "both"):
            if credentials and "username" in credentials:
                identifiers.append(credentials["username"])
            elif credentials and "email" in credentials:
                identifiers.append(credentials["email"])
        
        if self.identify_by in ("ip", "both"):
            client_ip = None
            if hasattr(request, 'client'):
                client_ip = request.client.host
            elif hasattr(request, 'remote_addr'):
                client_ip = request.remote_addr
            
            if client_ip:
                identifiers.append(f"ip:{client_ip}")
        
        return ":".join(identifiers) if identifiers else "unknown"
    
    async def check(self, request: Any, credentials: Optional[dict] = None) -> None:
        """Check rate limit before authentication attempt"""
        identifier = self._get_identifier(request, credentials)
        await self.limiter.check_rate_limit(identifier)
    
    async def record(self, request: Any, credentials: Optional[dict], success: bool) -> None:
        """Record authentication attempt result"""
        identifier = self._get_identifier(request, credentials)
        await self.limiter.record_attempt(identifier, success)
