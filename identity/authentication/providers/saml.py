"""SAML 2.0 authentication provider"""

from typing import Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from optorch.identity.authentication.provider import AuthenticationProvider
from optorch.identity.authentication.models import AuthResult, Individual
from optorch.identity.authentication.providers.config import SAMLProviderConfig
from optorch.logging import get_logger
from optorch.errors import AuthenticationError

if TYPE_CHECKING:
    from optorch.storage.manager import StorageManager
    from optorch.cache.manager import CacheManager
    from optorch.config.secrets.provider import SecretProvider

logger = get_logger(__name__)


class SAMLProvider(AuthenticationProvider):
    """SAML 2.0 authentication provider for enterprise SSO
    
    production implementation using python3-saml library
    """

    def __init__(
        self,
        config: SAMLProviderConfig,
        storage_manager: Optional["StorageManager"] = None,
        cache_manager: Optional["CacheManager"] = None,
        secrets_provider: Optional["SecretProvider"] = None,
    ):
        self.config = config
        self.storage = storage_manager
        self.cache_manager = cache_manager
        self.secrets_provider = secrets_provider
        
        self.idp_metadata_url = config.idp_metadata_url
        self.sp_entity_id = config.sp_entity_id
        self.acs_url = config.acs_url
        self.slo_url = config.slo_url
        self._priority = config.priority
        
        self._metadata_cache: Optional[dict] = None
        self._metadata_expires: Optional[datetime] = None
        
        self.saml_settings = self._build_saml_settings()

    def _build_saml_settings(self) -> dict:
        """build python3-saml settings dict"""
        
        sp_cert = None
        sp_key = None
        
        if self.secrets_provider:
            if self.config.sp_cert_secret:
                sp_cert = self.secrets_provider.get(self.config.sp_cert_secret)
            if self.config.sp_key_secret:
                sp_key = self.secrets_provider.get(self.config.sp_key_secret)
        
        settings = {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": self.sp_entity_id,
                "assertionConsumerService": {
                    "url": self.acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": self.slo_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                } if self.slo_url else None,
                "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
                "x509cert": sp_cert,
                "privateKey": sp_key
            },
            "idp": {
                "entityId": "",
                "singleSignOnService": {
                    "url": "",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": "",
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": ""
            },
            "security": {
                "nameIdEncrypted": False,
                "authnRequestsSigned": bool(sp_key),
                "logoutRequestSigned": bool(sp_key),
                "logoutResponseSigned": False,
                "signMetadata": False,
                "wantMessagesSigned": True,
                "wantAssertionsSigned": True,
                "wantNameId": True,
                "wantNameIdEncrypted": False,
                "wantAssertionsEncrypted": self.config.enable_encrypted_assertions,
                "signatureAlgorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
                "digestAlgorithm": "http://www.w3.org/2001/04/xmlenc#sha256"
            }
        }
        
        if self.slo_url is None:
            settings["sp"].pop("singleLogoutService", None)
        
        idp_data = self._fetch_idp_metadata()
        if idp_data:
            settings["idp"] = idp_data
        
        return settings
    
    def _fetch_idp_metadata(self) -> Optional[dict]:
        """fetch and parse idp metadata with caching"""
        
        now = datetime.now()
        if self._metadata_cache and self._metadata_expires and now < self._metadata_expires:
            return self._metadata_cache
        
        try:
            import httpx
            response = httpx.get(self.idp_metadata_url, timeout=10.0)
            if response.status_code == 200:
                from onelogin.saml2.idp_metadata_parser import OneLogin_Saml2_IdPMetadataParser
                idp_data = OneLogin_Saml2_IdPMetadataParser.parse(response.text)
                
                self._metadata_cache = idp_data["idp"]
                self._metadata_expires = now + timedelta(hours=self.config.metadata_refresh_hours)
                
                logger.info(f"loaded SAML IDP metadata (expires: {self._metadata_expires})")
                return self._metadata_cache
        except Exception as e:
            logger.warning(f"failed to load IDP metadata: {e}")
        
        return None
    
    def refresh_metadata(self) -> bool:
        """manually refresh idp metadata
        
        Returns:
            True if refresh successful
        """
        self._metadata_expires = None
        idp_data = self._fetch_idp_metadata()
        
        if idp_data:
            self.saml_settings["idp"] = idp_data
            return True
        
        return False

    def priority(self) -> int:
        """provider priority"""
        return self._priority
    
    def name(self) -> str:
        """provider name"""
        return "saml"

    async def authenticate(self, request: Any) -> AuthResult:
        """authenticate via SAML assertion
        
        Expects: request.form["SAMLResponse"] from IDP
        """
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        
        self._fetch_idp_metadata()
        
        saml_response = getattr(request, "form", {}).get("SAMLResponse")
        if not saml_response:
            return AuthResult(success=False, error="no SAML response in request")

        try:
            req = {
                "https": "on" if self.acs_url.startswith("https") else "off",
                "http_host": request.url.hostname,
                "script_name": request.url.path,
                "get_data": dict(request.query_params),
                "post_data": dict(request.form)
            }
            
            auth = OneLogin_Saml2_Auth(req, self.saml_settings)
            auth.process_response()
            
            errors = auth.get_errors()
            if errors:
                logger.error(f"SAML errors: {errors}")
                return AuthResult(success=False, error=f"SAML validation failed: {', '.join(errors)}")
            
            if not auth.is_authenticated():
                return AuthResult(success=False, error="SAML authentication failed")
            
            attributes = auth.get_attributes()
            name_id = auth.get_nameid() or "unknown"
            
            individual = Individual(
                id=name_id,
                email=attributes.get("email", [name_id])[0] if "email" in attributes else name_id,
                given_name=attributes.get("givenName", [None])[0] if "givenName" in attributes else None,
                family_name=attributes.get("surname", attributes.get("sn", [None]))[0] if "surname" in attributes or "sn" in attributes else None,
                metadata={
                    "provider": "saml",
                    "idp_entity_id": auth.get_attribute("issuer"),
                    "saml_attributes": attributes,
                    "session_index": auth.get_session_index()
                }
            )
            
            logger.info(f"SAML authentication successful: {name_id}")
            return AuthResult(success=True, individual=individual)

        except Exception as e:
            logger.error(f"saml authentication failed: {e}")
            return AuthResult(success=False, error=str(e))

    def can_handle(self, request: Any) -> bool:
        """check if request has SAML response"""
        return "SAMLResponse" in getattr(request, "form", {})
    
    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """SAML doesn't support refresh tokens - requires re-authentication
        
        Args:
            refresh_token: Ignored
            
        Returns:
            AuthResult with error explaining SAML limitation
        """
        return AuthResult(
            success=False, 
            error="SAML does not support refresh tokens - user must re-authenticate"
        )
    
    async def health_check(self) -> bool:
        """check if SAML IDP metadata is accessible"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.idp_metadata_url)
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"SAML health check failed: {e}")
            return False
    
    def get_login_url(self, relay_state: Optional[str] = None) -> str:
        """generate SAML login URL for IDP redirect
        
        Args:
            relay_state: URL to redirect after successful auth
        
        Returns:
            IDP SSO URL with SAML AuthnRequest
        """
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        
        req = {
            "https": "on" if self.acs_url.startswith("https") else "off",
            "http_host": "",
            "script_name": "",
            "get_data": {},
            "post_data": {}
        }
        
        auth = OneLogin_Saml2_Auth(req, self.saml_settings)
        return auth.login(return_to=relay_state)
    
    def get_logout_url(self, name_id: str, session_index: Optional[str] = None) -> str:
        """generate SAML logout URL for IDP redirect
        
        Args:
            name_id: user identifier from assertion
            session_index: SAML session index from assertion
        
        Returns:
            IDP SLO URL with SAML LogoutRequest
        """
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        
        req = {
            "https": "on" if self.acs_url.startswith("https") else "off",
            "http_host": "",
            "script_name": "",
            "get_data": {},
            "post_data": {}
        }
        
        auth = OneLogin_Saml2_Auth(req, self.saml_settings)
        return auth.logout(name_id=name_id, session_index=session_index)
    
    async def process_logout(self, request: Any) -> AuthResult:
        """process SAML logout request or response
        
        Handles both LogoutRequest from IDP and LogoutResponse from IDP.
        
        Args:
            request: FastAPI request with SAMLRequest or SAMLResponse
        
        Returns:
            AuthResult with logout URL or success status
        """
        from onelogin.saml2.auth import OneLogin_Saml2_Auth
        
        req = {
            "https": "on" if (self.slo_url or "").startswith("https") else "off",
            "http_host": request.url.hostname,
            "script_name": request.url.path,
            "get_data": dict(request.query_params),
            "post_data": {}
        }
        
        auth = OneLogin_Saml2_Auth(req, self.saml_settings)
        
        logout_request = request.query_params.get("SAMLRequest")
        logout_response = request.query_params.get("SAMLResponse")
        
        if logout_request:
            try:
                auth.process_slo(delete_session_cb=lambda: None)
                errors = auth.get_errors()
                if errors:
                    logger.error(f"SAML logout request errors: {errors}")
                    return AuthResult(success=False, error=f"SAML logout validation failed: {', '.join(errors)}")
                
                slo_url = auth.get_slo_url()
                
                return AuthResult(
                    success=True,
                    metadata={"logout_url": slo_url, "type": "logout_response"}
                )
            except Exception as e:
                logger.error(f"SAML logout request processing failed: {e}")
                return AuthResult(success=False, error=str(e))
        
        elif logout_response:
            try:
                auth.process_slo(delete_session_cb=lambda: None, keep_local_session=False)
                errors = auth.get_errors()
                if errors:
                    logger.error(f"SAML logout response errors: {errors}")
                    return AuthResult(success=False, error=f"SAML logout response validation failed: {', '.join(errors)}")
                
                return AuthResult(success=True, metadata={"type": "logout_complete"})
            except Exception as e:
                logger.error(f"SAML logout response processing failed: {e}")
                return AuthResult(success=False, error=str(e))
        
        return AuthResult(success=False, error="no SAMLRequest or SAMLResponse in logout request")

