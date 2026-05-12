import jwt
from typing import Optional, Any, Union, TYPE_CHECKING
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, ed448
from optorch.identity.authentication.models import Individual, AuthResult
from optorch.identity.authentication.providers.config import JWTProviderConfig
from optorch.logging import get_logger

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.config.secrets.provider import SecretProvider

logger = get_logger(__name__)


class JWTProvider:
    """JWT validation (no IDP - just token verification)"""
    
    def __init__(
        self,
        storage_manager: Optional["StorageManager"] = None,
        config: Optional[JWTProviderConfig] = None,
        secret_provider: Optional["SecretProvider"] = None,
        resolved_secret: Optional[str] = None,
        key_rotation: Optional[Any] = None
    ):
        self.storage = storage_manager
        self.config = config or JWTProviderConfig()
        self.secret_provider = secret_provider
        self.resolved_secret = resolved_secret or self.config.secret
        self.key_rotation = key_rotation
        
        algorithm = self.config.algorithm
        self.algorithm: str = algorithm
        self.audience: Optional[str] = self.config.audience
        self.issuer: Optional[str] = self.config.issuer
        
        self.public_key: Optional[Union[
            rsa.RSAPublicKey,
            ec.EllipticCurvePublicKey,
            ed25519.Ed25519PublicKey,
            ed448.Ed448PublicKey
        ]] = None
        if algorithm in ["RS256", "ES256"]:
            public_key_path = self.config.public_key_path
            if public_key_path:
                with open(public_key_path, "rb") as f:
                    loaded_key = serialization.load_pem_public_key(
                        f.read(),
                        backend=default_backend()
                    )

                    if isinstance(loaded_key, (
                        rsa.RSAPublicKey,
                        ec.EllipticCurvePublicKey,
                        ed25519.Ed25519PublicKey,
                        ed448.Ed448PublicKey
                    )):
                        self.public_key = loaded_key
                    else:
                        logger.warning(f"Loaded key type not supported: {type(loaded_key)}")
            else:
                logger.warning(f"Algorithm {algorithm} requires public_key_path")
    
    async def authenticate(self, request) -> AuthResult:
        """Authenticate by validating JWT from Authorization header or query param (for SSE)"""
        
        auth_header = getattr(request, 'headers', {}).get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
        else:
            # fallback to query param for SSE endpoints (EventSource can't send headers)
            query_params = getattr(request, 'query_params', {})
            token = query_params.get("token")
            if not token:
                return AuthResult(success=False, error="missing_token")
        
        try:
            if self.algorithm in ["RS256", "ES256"]:
                key = self.public_key
                if not key:
                    return AuthResult(success=False, error="no_public_key")
            else:
                # check if token has kid header indicating key rotation
                if self.key_rotation:
                    try:
                        unverified_header = jwt.get_unverified_header(token)
                        kid = unverified_header.get("kid")
                        if kid:
                            logger.info(f"JWT Provider: [VALIDATION] Token has kid={kid}, looking up rotated key")
                            key_info = await self.key_rotation.get_key_by_kid(kid)
                            if key_info:
                                key = key_info["secret"]
                                logger.info(f"JWT Provider: [VALIDATION] Using rotated key for kid={kid}")
                            else:
                                logger.warning(f"JWT Provider: kid={kid} not found, falling back to resolved_secret")
                                key = self.resolved_secret
                        else:
                            logger.debug("JWT Provider: no kid in token, using resolved_secret")
                            key = self.resolved_secret
                    except Exception as e:
                        logger.warning(f"JWT Provider: failed to extract kid from token: {e}, using resolved_secret")
                        key = self.resolved_secret
                else:
                    key = self.resolved_secret
                    
                if not key:
                    return AuthResult(success=False, error="no_secret")
            
            payload = jwt.decode(
                token,
                key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_signature": True}
            )
            
            individual = Individual(
                id=payload["sub"],
                email=payload.get("email"),
                name=payload.get("name"),
                current_org_id=payload.get("org_id"),
                roles=payload.get("roles", []),
                entitlements=payload.get("entitlements", []),
                metadata={"jwt_payload": payload}
            )
            
            return AuthResult(success=True, individual=individual, provider="jwt")
        
        except jwt.ExpiredSignatureError:
            return AuthResult(success=False, error="token_expired")
        
        except jwt.InvalidTokenError as e:
            return AuthResult(success=False, error=f"invalid_token: {e}")
        
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return AuthResult(success=False, error=f"validation_error: {e}")
    
    def priority(self) -> int:
        return 5  # check early, fast validation
    
    def name(self) -> str:
        return "jwt"
