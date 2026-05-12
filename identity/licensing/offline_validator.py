"""Offline license validation (RSA signature)"""

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
import json
import logging
from typing import Optional, cast, TYPE_CHECKING
from datetime import datetime, UTC

from optorch.identity.licensing.models import License

if TYPE_CHECKING:
    from optorch.identity.config import LicenseConfig

logger = logging.getLogger(__name__)


class OfflineValidator:
    """Validate license using RSA signature (air-gapped deployments)
    
    production features:
    - public key validation
    - JWT-based licenses as fallback
    - signature verification with proper error handling
    - expiry checking
    """

    def __init__(self, config: "LicenseConfig"):
        offline_config = config.offline
        public_key_path = offline_config.get("public_key_path", "/etc/optorch/license-public.pem")
        
        self.public_key: Optional[rsa.RSAPublicKey] = None
        self.air_gapped_mode = offline_config.get("air_gapped", False)
        
        try:
            with open(public_key_path, "rb") as f:
                key_data = f.read()
                self.public_key = cast(rsa.RSAPublicKey, serialization.load_pem_public_key(key_data))
                logger.info("loaded offline license public key")
        except FileNotFoundError:
            logger.warning(f"public key not found: {public_key_path}")
            if self.air_gapped_mode:
                from optorch.errors import ConfigurationError
                raise ConfigurationError("air-gapped mode requires public key")
        except Exception as e:
            logger.error(f"failed to load public key: {e}")
            raise

    def validate(self, license: License) -> bool:
        """verify RSA signature and expiry"""
        
        if not self._check_expiry(license):
            logger.warning(f"license expired: {license.uid}")
            return False
        
        if not license.signature:
            logger.warning("license missing signature")
            return False

        if not self.public_key:
            logger.error("public key not loaded")
            return False

        license_data = license.model_dump(exclude={"signature"}, mode='json')
        canonical_json = json.dumps(license_data, sort_keys=True).encode()

        try:
            self.public_key.verify(
                bytes.fromhex(license.signature),
                canonical_json,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256(),
            )
            logger.info(f"license signature valid: {license.uid}")
            return True

        except InvalidSignature:
            logger.error(f"invalid license signature: {license.uid}")
            return False
        except Exception as e:
            logger.error(f"signature verification failed: {e}")
            return False
    
    def _check_expiry(self, license: License) -> bool:
        """check license validity period"""
        now = datetime.now(UTC)
        
        if now < license.valid_from:
            logger.warning(f"license not yet valid: {license.uid} (valid from {license.valid_from})")
            return False
        
        if now > license.valid_until:
            logger.warning(f"license expired: {license.uid} (expired {license.valid_until})")
            return False
        
        return True
    
    def validate_jwt_license(self, jwt_token: str) -> bool:
        """validate JWT-based license (fallback for simple deployments)
        
        JWT contains:
        - iss: optorch-inc
        - sub: organization_id
        - exp: expiry timestamp
        - permissions: list of features
        """
        import jwt
        
        if not self.public_key:
            logger.error("public key required for JWT validation")
            return False
        
        try:
            pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            payload = jwt.decode(
                jwt_token,
                pem,
                algorithms=["RS256"],
                options={"verify_signature": True, "verify_exp": True}
            )
            
            logger.info(f"JWT license valid for org: {payload.get('sub')}")
            return True
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT license expired")
            return False
        except jwt.InvalidSignatureError:
            logger.error("JWT license signature invalid")
            return False
        except Exception as e:
            logger.error(f"JWT validation failed: {e}")
            return False
