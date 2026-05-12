from typing import Any, Optional
from pydantic import BaseModel
from optorch.identity.authentication.models import Individual, AuthResult
from optorch.identity.authentication.password.manager import PasswordManager
from optorch.identity.authentication.password.config import PasswordManagerConfig
from optorch.identity.authentication.providers.config import BuiltinProviderConfig, UserManagerConfig
from optorch.identity.authentication.providers.builtin.user_manager import UserManager
from optorch.errors import AuthenticationError
from optorch.logging import get_logger

logger = get_logger(__name__)


class Credentials(BaseModel):
    """Username/password credentials"""
    username: str
    password: str


class BuiltinAuthenticationProvider:
    """Username/password authentication with user management"""
    
    def __init__(
        self,
        storage_manager: Optional[Any] = None,
        notification_manager: Optional[Any] = None,
        secret_provider: Optional[Any] = None,
        config: Optional[BuiltinProviderConfig] = None,
        password_config: Optional[PasswordManagerConfig] = None
    ):
        self.storage = storage_manager
        self.notifications = notification_manager
        self.secret_provider = secret_provider
        self.config = config or BuiltinProviderConfig()
        
        self.password_manager = PasswordManager(password_config)
        
        if storage_manager:
            self.user_manager = UserManager(
                storage_manager=storage_manager,
                notification_manager=notification_manager,
                password_manager=self.password_manager,
                builtin_config=self.config,
                user_config=UserManagerConfig()
            )
        else:
            self.user_manager = None
    
    async def authenticate(self, request: Any) -> AuthResult:
        """Authenticate user with username/password"""
        
        if not self.storage:
            logger.error("No storage manager configured for builtin provider")
            return AuthResult(success=False, error="Storage not configured", provider="builtin")
        
        try:
            credentials = await self._extract_credentials(request)
        except AuthenticationError:
            return AuthResult(success=False, error="no_credentials", provider="builtin")
        
        user_data = await self.storage.query("identity.get_individual_by_email", email=credentials.username)
        
        if not user_data:
            logger.warning(f"Authentication failed: user not found - {credentials.username}")
            return AuthResult(success=False, error="Invalid credentials", provider="builtin")
        
        password_hash = user_data.get("password_hash")
        if not password_hash:
            logger.warning(f"Authentication failed: no password hash - {credentials.username}")
            return AuthResult(success=False, error="Invalid credentials", provider="builtin")
        
        if not self.password_manager.verify(credentials.password, password_hash):
            logger.warning(f"Authentication failed: invalid password - {credentials.username}")
            return AuthResult(success=False, error="Invalid credentials", provider="builtin")
        
        individual = Individual(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data.get("name"),
            given_name=user_data.get("given_name"),
            family_name=user_data.get("family_name"),
            current_org_id=user_data.get("organization_id"),
            roles=user_data.get("roles", []),
            entitlements=user_data.get("entitlements", []),
            metadata=user_data.get("metadata", {})
        )
        
        logger.info(f"Authentication successful: {credentials.username}")
        return AuthResult(success=True, individual=individual, provider="builtin")
    
    async def _extract_credentials(self, request: Any) -> Credentials:
        """Extract credentials from request
        
        Supports:
        - JSON body: {"username": "...", "password": "..."} or {"email": "...", "password": "..."}
        - Form data: username=...&password=...
        - Basic auth header: Authorization: Basic base64(username:password)
        """
        import inspect
        
        if hasattr(request, 'json'):
            try:
                json_method = request.json
                if callable(json_method):
                    if inspect.iscoroutinefunction(json_method):
                        body = await json_method()
                    else:
                        body = json_method()
                else:
                    body = json_method
                
                if isinstance(body, dict):
                    username = body.get("username") or body.get("email")
                    password = body.get("password")
                    if username and password:
                        return Credentials(username=username, password=password)
            except Exception:
                pass
        
        if hasattr(request, 'form'):
            try:
                form = request.form() if callable(request.form) else request.form
                if isinstance(form, dict) and "username" in form and "password" in form:
                    return Credentials(username=form["username"], password=form["password"])
            except Exception:
                pass
        
        if hasattr(request, 'headers'):
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Basic "):
                import base64
                try:
                    decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                    username, password = decoded.split(':', 1)
                    return Credentials(username=username, password=password)
                except Exception:
                    pass
        
        raise AuthenticationError("No credentials provided")
    
    def priority(self) -> int:
        return 20
    
    def name(self) -> str:
        return "builtin"
    
    async def health_check(self) -> bool:
        """check if database is accessible for builtin auth"""
        if not self.storage:
            return False
        
        try:
            result = await self.storage.query("identity.get_individual_by_email", email="__health_check__")
            return True
        except Exception as e:
            logger.debug(f"Builtin provider health check failed: {e}")
            return False

