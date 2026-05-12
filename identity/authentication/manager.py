"""Authentication manager - coordinates providers and JWT issuance"""

from typing import Optional, TYPE_CHECKING, Any, List
from optorch.identity.authentication.models import AuthResult, TokenPair, TokenClaims, Individual
from optorch.identity.authentication.health_check import ProviderHealthChecker
from optorch.identity.authentication.fallback_handler import FallbackHandler
from optorch.identity.authentication.rate_limiter import RateLimitMiddleware
from optorch.identity.authentication.key_rotation import KeyRotationManager
from optorch.identity.authentication.config import HealthCheckConfig, RateLimitConfig, FallbackConfig, KeyRotationConfig
from optorch.identity.audit import AuditLogger
from optorch.logging import get_logger
from datetime import datetime, timedelta, UTC
import jwt as pyjwt

if TYPE_CHECKING:
    from optorch.identity.authentication.provider import AuthenticationProvider
    from optorch.storage.manager import StorageManager
    from optorch.events.event_emitter import EventEmitter
    from optorch.cache.manager import CacheManager
    from optorch.config.secrets.provider import SecretProvider

logger = get_logger(__name__)


class AuthenticationManager:
    """Authentication manager - coordinates providers and JWT issuance
    
    Responsibilities:
    - Coordinate authentication providers (OIDC, SAML, JWT, Builtin)
    - Route requests to appropriate provider by priority
    - Issue optorch JWTs after IDP validation
    - Validate optorch JWTs on protected routes
    
    Flow:
    1. Request comes in → try providers by priority
    2. Provider authenticates → returns Individual
    3. Issue optorch JWT with claims
    4. Subsequent requests → validate JWT (fast, local)
    """
    
    def __init__(
        self,
        providers: List["AuthenticationProvider"],
        storage_manager: Optional["StorageManager"] = None,
        event_emitter: Optional["EventEmitter"] = None,
        cache_manager: Optional["CacheManager"] = None,
        secrets_provider: Optional["SecretProvider"] = None,
        enable_health_checks: bool = True,
        enable_rate_limiting: bool = True,
        enable_fallback: bool = True,
        enable_audit_logging: bool = True,
    ):
        """initialize authentication manager
        
        Args:
            providers: list of authentication providers (sorted by priority)
            storage_manager: for user lookups, refresh tokens
            event_emitter: for authentication events
            cache_manager: for token blacklisting
            secrets_provider: for secret resolution
            enable_health_checks: enable provider health monitoring
            enable_rate_limiting: enable rate limiting for login attempts
            enable_fallback: enable graceful fallback handling
            enable_audit_logging: enable audit logging for authentication events
        """
        self.providers_list = providers
        self.storage = storage_manager
        self.event_emitter = event_emitter
        self.cache_manager = cache_manager
        self.secrets_provider = secrets_provider
        self._jwt_secret = None
        
        self.health_checker: Optional[ProviderHealthChecker] = None
        if enable_health_checks and providers:
            self.health_checker = ProviderHealthChecker(providers=providers, config=HealthCheckConfig(), cache_manager=cache_manager)
        
        self.fallback_handler: Optional[FallbackHandler] = None
        if enable_fallback:
            self.fallback_handler = FallbackHandler(config=FallbackConfig(), event_emitter=event_emitter)
        
        self.rate_limiter: Optional[RateLimitMiddleware] = None
        if enable_rate_limiting:
            self.rate_limiter = RateLimitMiddleware(config=RateLimitConfig())
        
        self.key_rotation: Optional[KeyRotationManager] = None
        rotation_config = KeyRotationConfig()
        if storage_manager:
            self.key_rotation = KeyRotationManager(
                storage_manager=storage_manager,
                rotation_days=rotation_config.rotation_days,
                grace_period_days=rotation_config.grace_period_days,
                enable_auto_rotation=rotation_config.enable_auto_rotation,
                check_interval_hours=rotation_config.check_interval_hours
            )
            if rotation_config.enable_auto_rotation:
                self.key_rotation.start_rotation_task()
        
        self.audit_logger = AuditLogger(storage_manager=storage_manager, enabled=enable_audit_logging)
        
        self.jwt_config: dict[str, Any] = {}
        for p in providers:
            if p.__class__.__name__ == "JWTProvider":
                config_attr = getattr(p, "config", None)
                if config_attr and hasattr(config_attr, "model_dump"):
                    self.jwt_config = config_attr.model_dump()
                break

        self._sync_jwt_secret()
    
    def _sync_jwt_secret(self) -> None:
        """ensure JWT provider uses same secret as authentication manager"""
        jwt_secret = self._get_jwt_secret()
        
        jwt_provider_found = False
        for provider in self.providers_list:
            provider_name = provider.__class__.__name__
            if provider_name == "JWTProvider":
                jwt_provider_found = True
                setattr(provider, 'resolved_secret', jwt_secret)
                if self.key_rotation:
                    setattr(provider, 'key_rotation', self.key_rotation)
                break
        
        if not jwt_provider_found:
            logger.warning(f"[AUTH INIT] No JWTProvider found in providers list!")
    
    async def authenticate(
        self,
        request: Any,
        provider: Optional[str] = None,
        context: Optional[dict] = None
    ) -> AuthResult:
        """authenticate user from request using providers
        
        tries providers in priority order until one succeeds
        supports health checking, rate limiting, and fallback strategies
        
        Args:
            request: HTTP request object or credentials
            provider: specific provider name (or None for auto-selection)
            context: additional context
            
        Returns:
            AuthResult with success status and individual
        """
        ctx = context or {}
        
        has_bearer_token = False
        if hasattr(request, 'headers'):
            auth_header = request.headers.get('Authorization', '')
            has_bearer_token = auth_header.startswith('Bearer ')
        
        # Extract credentials for rate limiting
        credentials = self._extract_credentials(request) if not has_bearer_token else None
        has_credentials = credentials and any(k in credentials for k in ('email', 'username', 'password'))
        
        # Only rate limit actual authentication attempts (with credentials)
        # Skip rate limiting for: JWT validation, or requests with no credentials
        if self.rate_limiter and not has_bearer_token and has_credentials:
            try:
                await self.rate_limiter.check(request, credentials)
            except Exception as rate_error:
                if self.event_emitter:
                    self.event_emitter.emit("authentication.rate_limited", {"error": str(rate_error)})
                return AuthResult(success=False, error=str(rate_error))
        
        if provider:
            for p in self.providers_list:
                if p.__class__.__name__.replace("Provider", "").replace("Authentication", "").lower() == provider.lower():
                    result = await self._try_provider(p, request, ctx)
                    
                    # Record auth attempt (only for login attempts with credentials)
                    if self.rate_limiter and not has_bearer_token and has_credentials:
                        await self.rate_limiter.record(request, credentials, result.success)
                    if self.rate_limiter and not has_bearer_token:
                        await self.rate_limiter.record(request, credentials, result.success)
                    
                    if result.success:
                        result.provider = p.__class__.__name__
                    return result
            
            return AuthResult(success=False, error=f"Provider {provider} not found")
        
        if self.health_checker:
            available_providers = self.health_checker.get_healthy_providers()
        else:
            available_providers = self.providers_list
        
        if not available_providers:
            return AuthResult(success=False, error="No healthy providers available")
        
        sorted_providers = sorted(available_providers, key=lambda x: x.priority())
        
        last_error = None
        
        for p in sorted_providers:
            provider_name = p.__class__.__name__
            
            can_handle_method = getattr(p, "can_handle", None)
            if can_handle_method and not can_handle_method(request):
                continue
            
            if self.event_emitter:
                self.event_emitter.emit("authentication.provider_tried", {
                    "provider": provider_name
                })
            
            result = await self._try_provider(p, request, ctx)
            last_error = result.error
            
            if self.rate_limiter and not has_bearer_token and has_credentials:
                await self.rate_limiter.record(request, credentials, result.success)
            
            if result.success:
                result.provider = provider_name
                
                if self.event_emitter:
                    self.event_emitter.emit("authentication.success", {
                        "provider": provider_name,
                        "user_id": result.individual.id if result.individual else None
                    })
                
                if result.individual:
                    await self.audit_logger.log_authentication(
                        subject=result.individual.id,
                        action="login",
                        decision="success",
                        provider=provider_name,
                        reason="authenticated successfully"
                    )
                
                return result
        
        if self.event_emitter:
            self.event_emitter.emit("authentication.failed", {
                "providers_tried": len(sorted_providers),
                "error": last_error or "No provider could authenticate request"
            })
        
        credentials = self._extract_credentials(request)
        subject_id = credentials.get("username", "unknown") if credentials else "unknown"
        await self.audit_logger.log_authentication(
            subject=subject_id,
            action="login",
            decision="failure",
            provider="all_providers",
            reason=last_error or "no provider could authenticate"
        )
        
        return AuthResult(success=False, error=last_error or "No provider could authenticate request")
    
    async def _try_provider(self, provider: "AuthenticationProvider", request: Any, context: dict) -> AuthResult:
        """try authentication with fallback handling"""
        
        try:
            result = await provider.authenticate(request)
            return result
            
        except Exception as error:
            if self.fallback_handler:
                result = await self.fallback_handler.handle_failure(provider, request, error, context)
                if result:
                    return result
            
            return AuthResult(success=False, error=str(error))
    
    def _extract_credentials(self, request: Any) -> dict:
        """extract credentials for rate limiting"""
        
        creds = {}
        
        if hasattr(request, "email"):
            creds["email"] = request.email
        elif hasattr(request, "username"):
            creds["email"] = request.username
        # skip request.form and request.json - both are async in FastAPI
        # not needed for JWT bearer token auth anyway
        
        if hasattr(request, "client"):
            creds["ip"] = request.client.host
        elif hasattr(request, "remote_addr"):
            creds["ip"] = request.remote_addr
        
        return creds
    
    async def issue_token(
        self,
        individual: Individual,
        expires_in: Optional[int] = None,
        include_refresh_token: bool = False
    ) -> TokenPair:
        """Issue optorch JWT for authenticated individual
        
        Args:
            individual: Authenticated individual
            expires_in: Token lifetime in seconds (or use config default)
            include_refresh_token: Whether to include refresh token
        
        Returns:
            TokenPair with access_token and optional refresh_token
        """
        
        access_token_expire_minutes = self.jwt_config.get('access_token_expire_minutes', 60)
        final_expires_in = expires_in or (access_token_expire_minutes * 60)
        now = datetime.now(UTC)
        exp = now + timedelta(seconds=final_expires_in)
        
        claims = TokenClaims(
            sub=individual.id,
            email=individual.email,
            name=individual.name,
            org_id=individual.current_org_id,
            roles=individual.roles,
            entitlements=individual.entitlements,
            iss=self.jwt_config.get('issuer'),
            aud=self.jwt_config.get('audience'),
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            token_type="access",
            metadata=individual.metadata
        )
        
        if self.key_rotation:
            key_info = await self.key_rotation.get_current_key()
            secret = key_info["secret"]
            kid = key_info["kid"]
            algorithm = key_info.get("algorithm", "HS256")
        else:
            secret = self._get_jwt_secret()
            kid = None
            algorithm = self.jwt_config.get('algorithm', 'HS256')
        
        headers = {"kid": kid} if kid else {}
        access_token = pyjwt.encode(
            claims.model_dump(exclude_none=True),
            secret,
            algorithm=algorithm,
            headers=headers
        )
        
        await self.audit_logger.log_authentication(
            subject=individual.id,
            action="token_issued",
            decision="success",
            provider="jwt",
            reason=f"access token issued (expires_in={final_expires_in}s)"
        )
        
        token_pair = TokenPair(access_token=access_token, expires_in=final_expires_in, issued_at=now)
        
        if include_refresh_token:
            refresh_expire_days = self.jwt_config.get('refresh_token_expire_days', 30)
            refresh_exp = now + timedelta(days=refresh_expire_days)
            
            refresh_claims = TokenClaims(
                sub=individual.id,
                email=individual.email,
                name=individual.name,
                org_id=individual.current_org_id,
                roles=individual.roles,
                entitlements=individual.entitlements,
                iss=self.jwt_config.get('issuer'),
                aud=self.jwt_config.get('audience'),
                exp=int(refresh_exp.timestamp()),
                iat=int(now.timestamp()),
                token_type="refresh",
                metadata=individual.metadata
            )
            
            token_pair.refresh_token = pyjwt.encode(refresh_claims.model_dump(exclude_none=True), secret, algorithm=algorithm)
            
            await self.audit_logger.log_authentication(
                subject=individual.id,
                action="token_refreshed",
                decision="success",
                provider="jwt",
                reason=f"refresh token issued (expires_in={refresh_expire_days} days)"
            )
        
        return token_pair
    
    async def _get_jwt_key(self) -> dict:
        """Get current JWT signing key with rotation support"""
        
        if self.key_rotation:
            key = await self.key_rotation.get_current_key()
            return key
        
        if self._jwt_secret:
            return {"secret": self._jwt_secret, "algorithm": "HS256", "kid": "static"}
        
        direct_secret = self.jwt_config.get('secret')
        if direct_secret:
            self._jwt_secret = direct_secret
            return {"secret": self._jwt_secret, "algorithm": "HS256", "kid": "static"}
        
        secret_key_secret = self.jwt_config.get('secret_key_secret')
        if secret_key_secret and self.secrets_provider:
            secret = self.secrets_provider.get(secret_key_secret)
            if secret:
                self._jwt_secret = secret
                return {"secret": self._jwt_secret, "algorithm": "HS256", "kid": "static"}
            else:
                logger.error(f"JWT secret not found in secret provider: {secret_key_secret}")
        
        import secrets as py_secrets
        logger.warning("No JWT secret configured - generating random (NOT for production)")
        self._jwt_secret = py_secrets.token_urlsafe(32)
        return {"secret": self._jwt_secret, "algorithm": "HS256", "kid": "static"}
    
    def _get_jwt_secret(self) -> str:
        """Get JWT signing secret (cached) - DEPRECATED: use _get_jwt_key() instead"""
        
        if self._jwt_secret:
            return self._jwt_secret
        
        direct_secret = self.jwt_config.get('secret')
        if direct_secret:
            self._jwt_secret = direct_secret
            return self._jwt_secret
        
        secret_key_secret = self.jwt_config.get('secret_key_secret')
        if secret_key_secret and self.secrets_provider:
            secret = self.secrets_provider.get(secret_key_secret)
            if secret:
                self._jwt_secret = secret
                return self._jwt_secret
            else:
                logger.error(f"JWT secret not found in secret provider: {secret_key_secret}")
        
        import secrets as py_secrets
        logger.warning("No JWT secret configured - generating random (NOT for production)")
        self._jwt_secret = py_secrets.token_urlsafe(32)
        return self._jwt_secret
    
    def get_provider(self, name: str) -> Optional["AuthenticationProvider"]:
        """Get provider by name"""
        name_lower = name.lower()
        for p in self.providers_list:
            provider_name = p.__class__.__name__.replace("Provider", "").replace("Authentication", "").lower()
            if provider_name == name_lower:
                return p
        return None
    
    def has_provider(self, name: str) -> bool:
        """Check if provider exists"""
        return self.get_provider(name) is not None
    
    async def validate_refresh_token(self, refresh_token: str) -> Individual:
        """Validate refresh token and return Individual
        
        For builtin provider: validates JWT refresh token with key rotation support
        For OIDC/SAML: delegates to provider's refresh_token method
        
        Args:
            refresh_token: JWT refresh token or provider-specific token
            
        Returns:
            Individual if token valid
            
        Raises:
            AuthenticationError: Invalid/expired token
        """
        from optorch.errors import AuthenticationError
        
        algorithm = self.jwt_config.get('algorithm', 'HS256')
        
        keys_to_try = []
        if self.key_rotation:
            try:
                valid_keys = await self.key_rotation.get_verification_keys()
                keys_to_try = [(k["secret"], k.get("kid")) for k in valid_keys]
            except Exception as e:
                logger.warning(f"Failed to get rotation keys: {e}")
        
        if not keys_to_try:
            keys_to_try = [(self._get_jwt_secret(), None)]
        
        last_error = None
        for secret, kid in keys_to_try:
            try:
                decoded = pyjwt.decode(
                    refresh_token,
                    secret,
                    algorithms=[algorithm],
                    audience=self.jwt_config.get('audience'),
                    issuer=self.jwt_config.get('issuer')
                )
                
                if decoded.get("token_type") != "refresh":
                    raise AuthenticationError("Token is not a refresh token")
                
                individual = Individual(
                    id=decoded["sub"],
                    email=decoded.get("email"),
                    name=decoded.get("name"),
                    current_org_id=decoded.get("org_id"),
                    roles=decoded.get("roles", []),
                    entitlements=decoded.get("entitlements", []),
                    metadata=decoded.get("metadata", {})
                )
                
                return individual
                
            except pyjwt.ExpiredSignatureError:
                raise AuthenticationError("Refresh token expired")
            except pyjwt.InvalidTokenError as e:
                last_error = e
                continue
        
        for provider in self.providers_list:
            refresh_method = getattr(provider, 'refresh_token', None)
            if refresh_method:
                try:
                    new_token = await refresh_method(refresh_token)  # type: ignore[misc]
                    validate_method = getattr(provider, 'validate_token', None)
                    if validate_method:
                        individual = await validate_method(new_token.access_token)  # type: ignore[misc]
                        return individual
                except Exception as pe:
                    continue
        
        raise AuthenticationError("Invalid refresh token")
    
    async def cleanup(self) -> None:
        """cleanup authentication manager resources"""
        if self.key_rotation:
            await self.key_rotation.cleanup()
        
        if self.health_checker:
            await self.health_checker.stop()


