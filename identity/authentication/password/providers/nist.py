import bcrypt
import secrets
import string
import json
import math
import os
from typing import Optional, Any
from optorch.errors import ValidationError
from optorch.logging import get_logger
from optorch.identity.authentication.password.config import NISTPasswordConfig

logger = get_logger(__name__)


class NISTPasswordProvider:
    """NIST 800-63B compliant password provider
    
    Guidelines:
    - Min 8 chars (12+ recommended)
    - Max 64 chars
    - No composition rules (uppercase/special not required)
    - Check against common password lists
    - Use bcrypt (14+ rounds)
    
    Ref: https://pages.nist.gov/800-63-3/sp800-63b.html
    """
    
    def __init__(self, config: Optional[NISTPasswordConfig] = None):
        config = config or NISTPasswordConfig()
        self.min_length: int = config.min_length
        self.max_length: int = config.max_length
        self.bcrypt_rounds: int = config.bcrypt_rounds
        self.common_passwords: set[str] = self._load_common_passwords(config.common_passwords_file)
        self.wordlist: list[str] = self._load_wordlist(config.wordlist_file)
    
    def validate(self, password: str, context: Optional[dict[str, Any]] = None) -> None:
        """NIST validation - length + common password check"""
        
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
        
        if password.lower() in self.common_passwords:
            raise ValidationError(
                "Password is too common",
                details={"reason": "found_in_common_list"}
            )
    
    def hash(self, password: str) -> str:
        """Hash with bcrypt (14 rounds default)"""
        return bcrypt.hashpw(
            password.encode(),
            bcrypt.gensalt(rounds=self.bcrypt_rounds)
        ).decode()
    
    def verify(self, password: str, password_hash: str) -> bool:
        """Verify password against bcrypt hash"""
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except (ValueError, TypeError):
            return False
    
    def generate_temporary(self) -> str:
        """Generate random passphrase (XKCD-style)
        
        Example: "correct-horse-battery-staple-42"
        """
        words = self._get_random_words(4)
        number = secrets.randbelow(100)
        return f"{'-'.join(words)}-{number}"
    
    def strength_score(self, password: str) -> int:
        """Score based on entropy (not composition)"""
        
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
    
    def _load_common_passwords(self, filepath: Optional[str] = None) -> set[str]:
        """Load common passwords list from JSON file
        
        Args:
            filepath: Path to JSON file with common passwords array
                      Defaults to bundled list if not specified
        
        Returns:
            Set of lowercase common passwords
        """
        if not filepath:
            bundle_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "data",
                "common-passwords.json"
            )
            filepath = bundle_path
        
        try:
            with open(filepath, 'r') as f:
                passwords = json.load(f)
                return {pwd.lower() for pwd in passwords}
        except FileNotFoundError:
            logger.warning(f"Common passwords file not found: {filepath} - using empty set")
            return set()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in common passwords file: {filepath} - {e}")
            return set()
    
    def _load_wordlist(self, filepath: Optional[str] = None) -> list[str]:
        """Load EFF wordlist from JSON file
        
        Args:
            filepath: Path to JSON file with wordlist array
                      Defaults to bundled list if not specified
        
        Returns:
            List of words for passphrase generation
        """
        if not filepath:
            bundle_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "data",
                "eff-wordlist.json"
            )
            filepath = bundle_path
        
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"EFF wordlist not found: {filepath} - using fallback")
            return ["correct", "horse", "battery", "staple", "optorch", "secure"]
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in wordlist: {filepath} - {e}")
            return ["correct", "horse", "battery", "staple", "optorch", "secure"]
    
    def _get_random_words(self, count: int) -> list:
        """Get random words for passphrase from EFF wordlist
        
        Args:
            count: Number of random words to generate
            
        Returns:
            List of random words
        """
        return [secrets.choice(self.wordlist) for _ in range(count)]
