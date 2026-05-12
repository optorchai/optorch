"""OIDC authentication provider - Azure AD, Okta, Google"""

from typing import Any, Optional, TYPE_CHECKING
from optorch.identity.authentication.provider import AuthenticationProvider
from optorch.identity.authentication.models import AuthResult, Individual
from optorch.identity.authentication.providers.config import OIDCProviderConfig
from optorch.logging import get_logger
from optorch.errors import ConfigurationError, AuthenticationError
import httpx

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.cache.manager import CacheManager
    from optorch.config.secrets.provider import SecretProvider

logger = get_logger(__name__)


class OIDCProvider(AuthenticationProvider):
    """OAuth 2.0 / OIDC authentication provider
    
    Supports Azure AD, Okta, Google, Auth0, Keycloak
    """

    def __init__(
        self,
        config: OIDCProviderConfig,
        storage_manager: Optional["StorageManager"] = None,
        cache_manager: Optional["CacheManager"] = None,
        secrets_provider: Optional["SecretProvider"] = None,
    ):
        self.config = config
        self.storage = storage_manager
        self.cache_manager = cache_manager
        self.secrets_provider = secrets_provider
        
        self.issuer = config.issuer
        self.client_id_secret = config.client_id_secret
        self.client_secret_secret = config.client_secret_secret
        self.redirect_uri = config.redirect_uri
        self.scopes = config.scopes
        self._priority = config.priority
        
        self._discovery_cache: Optional[dict] = None
        self._jwks_cache: Optional[dict] = None
        self._jwks_cache_time: Optional[float] = None
        self._jwks_cache_ttl: int = 3600  # 1 hour

    def priority(self) -> int:
        """provider priority"""
        return self._priority
    
    def name(self) -> str:
        """provider name"""
        return "oidc"

    async def authenticate(self, request: Any) -> AuthResult:
        """authenticate via OIDC authorization code flow
        
        Expects: request.query_params["code"] from IDP redirect
        """
        code = getattr(request, "query_params", {}).get("code")
        if not code:
            return AuthResult(success=False, error="no authorization code in request")

        try:
            token_response = await self._exchange_code_for_tokens(code)
            
            id_token = token_response.get("id_token")
            access_token = token_response.get("access_token")
            
            if not access_token:
                return AuthResult(success=False, error="no access token in response")
            
            if id_token:
                try:
                    await self._verify_id_token(id_token)
                except Exception as e:
                    logger.warning(f"ID token verification failed: {e}")
                    return AuthResult(success=False, error=f"ID token verification failed: {e}")
            
            user_info = await self._get_userinfo(access_token)
            
            sub = user_info.get("sub")
            if not sub:
                return AuthResult(success=False, error="no subject in user info")
            
            individual = Individual(
                id=sub,
                email=user_info.get("email"),
                given_name=user_info.get("given_name"),
                family_name=user_info.get("family_name"),
                metadata={
                    "provider": "oidc",
                    "issuer": self.issuer,
                    "id_token_claims": id_token
                }
            )
            
            return AuthResult(success=True, individual=individual)

        except Exception as e:
            logger.error(f"oidc authentication failed: {e}")
            return AuthResult(success=False, error=str(e))

    async def _exchange_code_for_tokens(self, code: str) -> dict:
        """exchange authorization code for tokens"""
        discovery = await self._get_discovery_document()
        token_endpoint = discovery["token_endpoint"]
        
        if not self.client_id_secret or not self.client_secret_secret:
            raise ConfigurationError(
                "client_id_secret and client_secret_secret required for OIDC",
                details={"issuer": self.issuer}
            )
        
        client_id = await self._resolve_secret(self.client_id_secret)
        client_secret = await self._resolve_secret(self.client_secret_secret)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": self.redirect_uri
                }
            )
            response.raise_for_status()
            return response.json()

    async def _get_userinfo(self, access_token: str) -> dict:
        """fetch user info from userinfo endpoint"""
        discovery = await self._get_discovery_document()
        userinfo_endpoint = discovery["userinfo_endpoint"]
        
        async with httpx.AsyncClient() as client:
            response = await client.get(userinfo_endpoint, headers={"Authorization": f"Bearer {access_token}"})
            response.raise_for_status()
            return response.json()

    async def _get_discovery_document(self) -> dict:
        """fetch OIDC discovery document with caching"""
        if self._discovery_cache is not None:
            return self._discovery_cache
        
        discovery_url = f"{self.issuer}/.well-known/openid-configuration"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(discovery_url)
            response.raise_for_status()
            discovery = response.json()
            self._discovery_cache = discovery
            return discovery
    
    async def _get_jwks(self) -> dict:
        """fetch JWKS with caching"""
        import time
        
        if self._jwks_cache and self._jwks_cache_time:
            if time.time() - self._jwks_cache_time < self._jwks_cache_ttl:
                return self._jwks_cache
        
        discovery = await self._get_discovery_document()
        jwks_uri = discovery.get("jwks_uri")
        
        if not jwks_uri:
            raise ConfigurationError("No jwks_uri in discovery document", details={"issuer": self.issuer})
        
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_uri)
            response.raise_for_status()
            jwks = response.json()
            
            self._jwks_cache = jwks
            self._jwks_cache_time = time.time()
            
            return jwks
    
    async def _verify_id_token(self, id_token: str) -> dict:
        """verify ID token signature and claims"""
        import jwt as pyjwt
        from jwt import PyJWKClient
        
        discovery = await self._get_discovery_document()
        jwks_uri = discovery.get("jwks_uri")
        
        if not jwks_uri:
            raise ConfigurationError(
                "No jwks_uri in discovery document",
                details={"issuer": self.issuer}
            )
        
        jwks_client = PyJWKClient(jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        
        try:
            decoded = pyjwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=await self._resolve_secret(self.client_id_secret) if self.client_id_secret else None,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True
                }
            )
            return decoded
        except pyjwt.ExpiredSignatureError:
            raise AuthenticationError("ID token expired")
        except pyjwt.InvalidAudienceError:
            raise AuthenticationError("ID token audience mismatch")
        except pyjwt.InvalidIssuerError:
            raise AuthenticationError("ID token issuer mismatch")
        except pyjwt.InvalidSignatureError:
            raise AuthenticationError("ID token signature invalid")

    async def _resolve_secret(self, secret_key: str) -> str:
        """resolve secret from secrets provider"""
        if not self.secrets_provider:
            raise ConfigurationError(
                "secrets provider required for OIDC but not configured",
                details={"secret_key": secret_key, "issuer": self.issuer}
            )
        
        result = self.secrets_provider.get(secret_key)
        if result is None:
            raise ConfigurationError(f"secret not found: {secret_key}", details={"issuer": self.issuer})
        return result

    def can_handle(self, request: Any) -> bool:
        """check if request has OIDC authorization code"""
        return "code" in getattr(request, "query_params", {})
    
    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """refresh access token using refresh token
        
        Args:
            refresh_token: OIDC refresh token from token endpoint
            
        Returns:
            AuthResult with updated individual and tokens
        """
        try:
            discovery = await self._get_discovery_document()
            token_endpoint = discovery["token_endpoint"]
            
            client_id = await self._resolve_secret(self.client_id_secret)
            client_secret = await self._resolve_secret(self.client_secret_secret)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_endpoint,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": client_id,
                        "client_secret": client_secret
                    }
                )
                response.raise_for_status()
                token_response = response.json()
            
            access_token = token_response.get("access_token")
            if not access_token:
                return AuthResult(success=False, error="no access token in refresh response")
            
            user_info = await self._get_userinfo(access_token)
            
            sub = user_info.get("sub")
            if not sub:
                return AuthResult(success=False, error="no subject in user info")
            
            individual = Individual(
                id=sub,
                email=user_info.get("email"),
                given_name=user_info.get("given_name"),
                family_name=user_info.get("family_name"),
                metadata={
                    "provider": "oidc",
                    "issuer": self.issuer,
                    "refreshed": True
                }
            )
            
            return AuthResult(success=True, individual=individual)
            
        except Exception as e:
            logger.error(f"OIDC refresh token failed: {e}")
            return AuthResult(success=False, error=str(e))
    
    async def health_check(self) -> bool:
        """check if OIDC provider is healthy by pinging discovery endpoint"""
        try:
            discovery_url = f"{self.issuer}/.well-known/openid-configuration"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(discovery_url)
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"OIDC health check failed: {e}")
            return False

