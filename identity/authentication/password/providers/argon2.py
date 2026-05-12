import secrets
import string
from typing import Optional, Any
from optorch.errors import ValidationError
from optorch.logging import get_logger
from optorch.identity.authentication.password.config import Argon2PasswordConfig

logger = get_logger(__name__)

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, InvalidHash
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    logger.warning("argon2-cffi not installed - Argon2PasswordProvider will not be available")


class Argon2PasswordProvider:
    """Argon2id password provider (winner of Password Hashing Competition)
    
    Advantages over bcrypt:
    - Memory-hard (GPU/ASIC resistant)
    - Configurable time/memory/parallelism
    - Recommended by OWASP 2023
    
    Requires: pip install argon2-cffi
    """
    
    def __init__(self, config: Optional[Argon2PasswordConfig] = None):
        if not ARGON2_AVAILABLE:
            raise ImportError(
                "argon2-cffi is required for Argon2PasswordProvider. "
                "Install with: pip install argon2-cffi"
            )
        
        cfg = config or Argon2PasswordConfig()
        self.min_length = cfg.min_length
        self.max_length = cfg.max_length
        
        self.hasher = PasswordHasher(
            time_cost=cfg.time_cost,
            memory_cost=cfg.memory_cost,
            parallelism=cfg.parallelism,
            hash_len=cfg.hash_len,
            salt_len=cfg.salt_len
        )
    
    def validate(self, password: str, context: Optional[dict[str, Any]] = None) -> None:
        """Simple length check (NIST-style)"""
        
        if len(password) < self.min_length:
            raise ValidationError(
                f"Password must be at least {self.min_length} characters",
                details={"min_length": self.min_length, "actual": len(password)}
            )
        
        if len(password) > self.max_length:
            raise ValidationError(
                f"Password must be at most {self.max_length} characters",
                details={"max_length": self.max_length, "actual": len(password)}
            )
    
    def hash(self, password: str) -> str:
        """Hash with Argon2id"""
        return self.hasher.hash(password)
    
    def verify(self, password: str, password_hash: str) -> bool:
        """Verify with Argon2id"""
        try:
            self.hasher.verify(password_hash, password)
            return True
        except (VerifyMismatchError, InvalidHash):
            return False
    
    def generate_temporary(self) -> str:
        """Generate random passphrase (XKCD-style)"""
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(16))
    
    def strength_score(self, password: str) -> int:
        """Score based on entropy"""
        import math
        
        charset_size = 0
        if any(c.islower() for c in password):
            charset_size += 26
        if any(c.isupper() for c in password):
            charset_size += 26
        if any(c.isdigit() for c in password):
            charset_size += 10
        if any(c in string.punctuation for c in password):
            charset_size += len(string.punctuation)
        
        entropy = len(password) * math.log2(charset_size) if charset_size > 0 else 0
        score = min(int((entropy / 60) * 100), 100)
        return score
