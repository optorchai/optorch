import bcrypt
import secrets
import string
import re
from typing import Optional, Any
from optorch.errors import ValidationError
from optorch.logging import get_logger
from optorch.identity.authentication.password.config import EnterprisePasswordConfig

logger = get_logger(__name__)


class EnterprisePasswordProvider:
    """Traditional enterprise password provider with complex requirements
    
    Requirements:
    - 14+ characters (configurable)
    - Uppercase, lowercase, digit, special char (configurable)
    - No username/email in password
    - No consecutive repeated characters
    - bcrypt hashing
    """
    
    def __init__(self, config: Optional[EnterprisePasswordConfig] = None):
        cfg = config or EnterprisePasswordConfig()
        self.min_length = cfg.min_length
        self.require_uppercase = cfg.require_uppercase
        self.require_lowercase = cfg.require_lowercase
        self.require_digit = cfg.require_digit
        self.require_special = cfg.require_special
        self.special_chars = cfg.special_chars
        self.bcrypt_rounds = cfg.bcrypt_rounds
        self.max_consecutive_chars = cfg.max_consecutive_chars
    
    def validate(self, password: str, context: Optional[dict[str, Any]] = None) -> None:
        """Strict enterprise validation"""
        
        if len(password) < self.min_length:
            raise ValidationError(
                f"Password must be at least {self.min_length} characters",
                details={"min_length": self.min_length}
            )
        
        checks = {
            "uppercase": (self.require_uppercase, any(c.isupper() for c in password)),
            "lowercase": (self.require_lowercase, any(c.islower() for c in password)),
            "digit": (self.require_digit, any(c.isdigit() for c in password)),
            "special": (self.require_special, any(c in self.special_chars for c in password))
        }
        
        missing = [name for name, (required, present) in checks.items() if required and not present]
        
        if missing:
            raise ValidationError(
                f"Password must contain: {', '.join(missing)}",
                details={"missing_requirements": missing}
            )
        
        if self._has_consecutive_repeats(password, self.max_consecutive_chars):
            raise ValidationError(
                f"Password cannot have more than {self.max_consecutive_chars} consecutive identical characters",
                details={"max_consecutive": self.max_consecutive_chars}
            )
        
        if context:
            email = context.get("email", "").lower()
            username = email.split("@")[0] if email else ""
            
            if username and username in password.lower():
                raise ValidationError(
                    "Password cannot contain username or email",
                    details={"reason": "contains_username"}
                )
    
    def hash(self, password: str) -> str:
        """Hash with bcrypt"""
        return bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt(rounds=self.bcrypt_rounds)
        ).decode()
    
    def verify(self, password: str, password_hash: str) -> bool:
        """Verify with bcrypt"""
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except (ValueError, TypeError):
            return False
    
    def generate_temporary(self) -> str:
        """Generate complex random password meeting all requirements"""
        uppercase = secrets.choice(string.ascii_uppercase)
        lowercase = secrets.choice(string.ascii_lowercase)
        digit = secrets.choice(string.digits)
        special = secrets.choice(self.special_chars)
        
        remaining_length = self.min_length - 4
        all_chars = string.ascii_letters + string.digits + self.special_chars
        remaining = ''.join(secrets.choice(all_chars) for _ in range(remaining_length))
        
        chars = list(uppercase + lowercase + digit + special + remaining)
        secrets.SystemRandom().shuffle(chars)
        
        return ''.join(chars)
    
    def strength_score(self, password: str) -> int:
        """Score based on requirements met + length"""
        score = 0
        score += min(len(password) * 2, 40)
        
        if any(c.isupper() for c in password):
            score += 15
        if any(c.islower() for c in password):
            score += 15
        if any(c.isdigit() for c in password):
            score += 15
        if any(c in self.special_chars for c in password):
            score += 15
        
        return min(score, 100)
    
    def _has_consecutive_repeats(self, password: str, max_count: int) -> bool:
        """Check for consecutive repeated characters"""
        return bool(re.search(rf'(.)\1{{{max_count},}}', password))
