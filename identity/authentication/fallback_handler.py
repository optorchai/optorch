"""Graceful fallback handling for authentication failures"""

from typing import TYPE_CHECKING, Optional, Any
from optorch.logging import get_logger
from optorch.identity.authentication.models import AuthResult
from optorch.identity.authentication.config import RetryConfig, CacheConfig, FallbackConfig
from datetime import datetime, UTC

if TYPE_CHECKING:
    from optorch.identity.authentication.provider import AuthenticationProvider
    from optorch.events.event_emitter import EventEmitter

logger = get_logger(__name__)


class FallbackStrategy:
    """Base fallback strategy"""
    
    async def handle(
        self,
        provider: "AuthenticationProvider",
        error: Exception,
        request: Any,
        context: dict
    ) -> Optional[AuthResult]:
        """Handle provider failure, return None to try next provider"""
        return None


class RetryStrategy(FallbackStrategy):
    """Retry failed provider with exponential backoff"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        cfg = config or RetryConfig()
        self.max_retries = cfg.max_attempts
        self.base_delay = cfg.base_delay
    
    async def handle(
        self,
        provider: "AuthenticationProvider",
        error: Exception,
        request: Any,
        context: dict
    ) -> Optional[AuthResult]:
        import asyncio
        
        for attempt in range(self.max_retries):
            delay = self.base_delay * (2 ** attempt)
            logger.debug(f"retrying {provider.__class__.__name__} after {delay}s (attempt {attempt + 1}/{self.max_retries})")
            await asyncio.sleep(delay)
            
            try:
                result = await provider.authenticate(request)
                if result.success:
                    logger.info(f"retry succeeded for {provider.__class__.__name__} on attempt {attempt + 1}")
                    return result
            except Exception as retry_error:
                logger.debug(f"retry attempt {attempt + 1} failed: {retry_error}")
                continue
        
        return None


class CachedAuthStrategy(FallbackStrategy):
    """Use cached authentication for temporary failures"""
    
    def __init__(self, config: Optional[CacheConfig] = None):
        cfg = config or CacheConfig()
        self.cache_ttl = cfg.ttl_seconds
        self._cache: dict[str, tuple[AuthResult, datetime]] = {}
    
    async def handle(
        self,
        provider: "AuthenticationProvider",
        error: Exception,
        request: Any,
        context: dict
    ) -> Optional[AuthResult]:
        user_id = self._extract_user_id(request, context)
        if not user_id:
            return None
        
        cache_key = f"{provider.__class__.__name__}:{user_id}"
        cached = self._cache.get(cache_key)
        
        if cached:
            result, cached_at = cached
            age = (datetime.now(UTC) - cached_at).total_seconds()
            
            if age < self.cache_ttl:
                logger.warning(f"using cached auth for {user_id} (age: {age}s) due to provider failure")
                return result
        
        return None
    
    def _extract_user_id(self, request: Any, context: dict) -> Optional[str]:
        if "user_id" in context:
            return context["user_id"]

        if hasattr(request, 'headers'):
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                try:
                    import jwt
                    claims = jwt.decode(token, options={"verify_signature": False})
                    return claims.get("sub")
                except Exception:
                    return None

        return None
    
    def cache_success(self, provider: "AuthenticationProvider", user_id: str, result: AuthResult) -> None:
        """Cache successful authentication"""
        cache_key = f"{provider.__class__.__name__}:{user_id}"
        self._cache[cache_key] = (result, datetime.now(UTC))


class FallbackHandler:
    """Manages fallback strategies for provider failures"""
    
    def __init__(
        self,
        config: Optional[FallbackConfig] = None,
        event_emitter: Optional["EventEmitter"] = None
    ):
        self.event_emitter = event_emitter
        self.strategies: list[FallbackStrategy] = []
        cfg = config or FallbackConfig()
        
        if cfg.enable_retry and cfg.retry:
            self.strategies.append(RetryStrategy(config=cfg.retry))
        
        if cfg.enable_cache and cfg.cache:
            self.strategies.append(CachedAuthStrategy(config=cfg.cache))
    
    async def handle_failure(
        self,
        provider: "AuthenticationProvider",
        error: Exception,
        request: Any,
        context: Optional[dict] = None
    ) -> Optional[AuthResult]:
        """Handle provider failure using configured strategies"""
        ctx = context or {}
        provider_name = provider.__class__.__name__
        
        logger.warning(f"provider {provider_name} failed: {error}")
        
        if self.event_emitter:
            self.event_emitter.emit("authentication.provider_failed", {
                "provider": provider_name,
                "error": str(error),
                "error_type": type(error).__name__
            })
        
        for strategy in self.strategies:
            try:
                result = await strategy.handle(provider, error, request, ctx)
                if result and result.success:
                    logger.info(f"fallback strategy {strategy.__class__.__name__} succeeded for {provider_name}")
                    
                    if self.event_emitter:
                        self.event_emitter.emit("authentication.fallback_success", {
                            "provider": provider_name,
                            "strategy": strategy.__class__.__name__
                        })
                    
                    return result
            except Exception as strategy_error:
                logger.debug(f"fallback strategy {strategy.__class__.__name__} failed: {strategy_error}")
                continue
        
        return None
    
    def add_strategy(self, strategy: FallbackStrategy) -> None:
        """Add custom fallback strategy"""
        self.strategies.append(strategy)
