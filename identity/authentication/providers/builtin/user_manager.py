from typing import Optional, Any
from datetime import datetime, timedelta, UTC
import secrets
import json
from optorch.identity.authentication.models import Individual
from optorch.identity.authentication.password.manager import PasswordManager
from optorch.identity.authentication.providers.config import UserManagerConfig, BuiltinProviderConfig
from optorch.errors import ValidationError
from optorch.logging import get_logger

logger = get_logger(__name__)


class UserManager:
    """User lifecycle management for builtin provider"""
    
    def __init__(
        self,
        storage_manager: Any,
        notification_manager: Any,
        password_manager: PasswordManager,
        builtin_config: Optional[BuiltinProviderConfig] = None,
        user_config: Optional[UserManagerConfig] = None
    ):
        self.storage = storage_manager
        self.notifications = notification_manager
        self.password_manager = password_manager
        self.builtin_config = builtin_config or BuiltinProviderConfig()
        self.user_config = user_config or UserManagerConfig()
    
    async def create_individual(
        self,
        email: str,
        name: str,
        organization_id: int,
        roles: Optional[list[str]] = None,
        send_invite: bool = True,
        password: Optional[str] = None
    ) -> Individual:
        """Create new builtin individual with optional invite
        
        Args:
            email: Individual's email address
            name: Full name
            organization_id: Organization ID to join
            roles: Initial roles (defaults to ["member"])
            send_invite: Send invitation email with setup link
            password: Optional initial password (if not sent, generates random)
        
        Returns:
            Created Individual
            
        Raises:
            ValidationError: Email already exists
            ConfigurationError: Notification manager not configured
        """
        existing = await self.storage.query("identity.get_individual_by_email", email=email)
        
        if existing:
            raise ValidationError(
                f"Individual with email {email} already exists",
                details={"email": email, "existing_id": existing.get("id")}
            )
        
        if not password:
            password = self.password_manager.generate_temporary()
        
        self.password_manager.validate(password)
        password_hash = self.password_manager.hash(password)
        individual_id = f"builtin-{secrets.token_urlsafe(12)}"
        
        parts = name.split(" ", 1)
        given_name = parts[0] if parts else ""
        family_name = parts[1] if len(parts) > 1 else ""
        
        from optorch.identity.organization.models import Individual as PersistentIndividual
        
        persistent_individual = PersistentIndividual(
            id=individual_id,
            given_name=given_name,
            family_name=family_name,
            email=email,
            password_hash=password_hash,
            status="active",
            metadata={
                "provider": "builtin",
                "created_at": datetime.now(UTC).isoformat(),
                "invite_sent": send_invite
            }
        )
        
        await self.storage.query("identity.create_individual", individual=persistent_individual)
        
        individual = Individual(
            id=individual_id,
            email=email,
            name=name,
            given_name=given_name,
            family_name=family_name,
            current_org_id=str(organization_id),
            roles=roles or ["member"],
            metadata=persistent_individual.metadata
        )
        
        await self.storage.query("identity.create_membership", individual_id=individual.id, organization_id=organization_id, roles=individual.roles)
        
        if send_invite:
            await self.send_invite(individual=individual, temporary_password=password)
        
        logger.info(f"Created individual: {email} (id={individual.id})")
        return individual
    
    async def send_invite(
        self,
        individual: Individual,
        temporary_password: Optional[str] = None
    ) -> str:
        """Send invitation email with setup link
        
        Args:
            individual: Individual to invite
            temporary_password: Optional temp password (if provided, skip reset token)
            
        Returns:
            Invite token (for testing/verification)
        """
        invite_token = secrets.token_urlsafe(32)
        expiry_hours = self.user_config.invite_expiry_hours
        expiry = datetime.now(UTC) + timedelta(hours=expiry_hours)
        
        await self.storage.query(
            "identity.create_invite_token",
            individual_id=individual.id,
            token=invite_token,
            expiry=expiry,
            created_by="system"
        )
        
        base_url = self.builtin_config.base_url
        invite_url_template = self.builtin_config.invite_url_template
        invite_link = invite_url_template.replace("{{base_url}}", base_url).replace("{{token}}", invite_token)
        
        if not self.notifications:
            logger.warning(f"notification manager not configured - skipping invite email for {individual.email}")
            logger.info(f"invite token for {individual.email}: {invite_token} (expires in {expiry_hours}h)")
            logger.info(f"invite link: {invite_link}")
            if temporary_password:
                logger.info(f"temporary password: {temporary_password}")
            return invite_token
        
        await self.notifications.send(
            event_type="user.invite",
            recipient=individual.email,
            context={
                "individual_name": individual.name,
                "organization_id": individual.current_org_id,
                "invite_link": invite_link,
                "temporary_password": temporary_password,
                "expiry_hours": expiry_hours
            }
        )
        
        logger.info(f"Sent invite to {individual.email} (token={invite_token[:8]}...)")
        return invite_token
    
    async def accept_invite(
        self,
        token: str,
        new_password: str
    ) -> Individual:
        """Accept invite and set password
        
        Args:
            token: Invite token from email
            new_password: New password to set
            
        Returns:
            Activated Individual
            
        Raises:
            ValidationError: Invalid/expired token, weak password
        """
        invite = await self.storage.query("identity.get_invite_token", token=token)
        
        if not invite:
            raise ValidationError("Invalid invite token", details={"token": token[:8] + "..."})
        
        if datetime.fromisoformat(invite["expiry"]).replace(tzinfo=UTC) < datetime.now(UTC):
            raise ValidationError(
                "Invite token expired",
                details={
                    "token": token[:8] + "...",
                    "expired_at": invite["expiry"]
                }
            )
        
        self.password_manager.validate(new_password)
        password_hash = self.password_manager.hash(new_password)
        
        await self.storage.query("identity.update_individual_password", individual_id=invite["individual_id"], password_hash=password_hash)
        await self.storage.query("identity.invalidate_invite_token", token=token)
        
        individual_data = await self.storage.query("identity.get_individual", individual_id=invite["individual_id"])
        logger.info(f"Invite accepted: {individual_data['email']}")
        return Individual(**individual_data)
    
    async def reset_password_request(
        self,
        email: str,
        notification_channel: str = "email"
    ) -> str:
        """Initiate password reset flow
        
        Args:
            email: Individual's email
            notification_channel: "email" | "sms" | "push"
            
        Returns:
            Reset token (for testing)
            
        Raises:
            ValidationError: Individual not found, not builtin provider
        """
        individual_data = await self.storage.query("identity.get_individual_by_email", email=email)
        
        if not individual_data:
            logger.warning(f"Password reset requested for unknown email: {email}")
            return ""
        
        if individual_data.get("metadata", {}).get("provider") != "builtin":
            raise ValidationError(
                "Cannot reset password for federated individuals",
                details={
                    "email": email,
                    "provider": individual_data.get("metadata", {}).get("provider")
                }
            )
        
        reset_token = secrets.token_urlsafe(32)
        expiry_hours = self.user_config.password_reset_expiry_hours
        expiry = datetime.now(UTC) + timedelta(hours=expiry_hours)
        
        await self.storage.query(
            "identity.create_reset_token",
            individual_id=individual_data["id"],
            token=reset_token,
            expiry=expiry
        )
        
        base_url = self.builtin_config.base_url
        password_reset_url_template = self.builtin_config.password_reset_url_template
        reset_link = password_reset_url_template.replace("{{base_url}}", base_url).replace("{{token}}", reset_token)
        
        if self.notifications:
            await self.notifications.send(
                event_type="user.password_reset",
                recipient=email,
                context={
                    "individual_name": individual_data.get("name"),
                    "reset_link": reset_link,
                    "expiry_hours": expiry_hours
                },
                channels=[notification_channel] if notification_channel != "email" else None
            )
        else:
            logger.warning(f"notification manager not configured - skipping password reset email for {email}")
            logger.info(f"password reset token for {email}: {reset_token} (expires in {expiry_hours}h)")
            logger.info(f"reset link: {reset_link}")
        
        logger.info(f"Password reset initiated: {email}")
        return reset_token
    
    async def reset_password_confirm(
        self,
        token: str,
        new_password: str
    ) -> Individual:
        """Complete password reset
        
        Args:
            token: Reset token from email/SMS
            new_password: New password
            
        Returns:
            Updated Individual
            
        Raises:
            ValidationError: Invalid/expired token, weak password
        """
        reset = await self.storage.query("identity.get_reset_token", token=token)
        
        if not reset:
            raise ValidationError("Invalid reset token", details={"token": token[:8] + "..."})
        
        if datetime.fromisoformat(reset["expiry"]).replace(tzinfo=UTC) < datetime.now(UTC):
            raise ValidationError(
                "Reset token expired",
                details={
                    "token": token[:8] + "...",
                    "expired_at": reset["expiry"]
                }
            )
        
        self.password_manager.validate(new_password)
        password_hash = self.password_manager.hash(new_password)
        
        await self.storage.query("identity.update_individual_password", individual_id=reset["individual_id"], password_hash=password_hash)
        await self.storage.query("identity.invalidate_reset_token", token=token)

        individual_data = await self.storage.query("identity.get_individual", individual_id=reset["individual_id"])
        
        logger.info(f"Password reset completed: {individual_data['email']}")
        return Individual(**individual_data)