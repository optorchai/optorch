from typing import Protocol, Optional, Any
from optorch.errors import ValidationError


class PasswordProvider(Protocol):
    """Provider implementation for password operations"""
    
    def validate(self, password: str, context: Optional[dict[str, Any]] = None) -> None:
        """Validate password meets requirements
        
        Args:
            password: Plain text password
            context: Optional context (email, username, etc)
            
        Raises:
            ValidationError: Password doesn't meet requirements
        """
        ...
    
    def hash(self, password: str) -> str:
        """Hash password for storage
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        ...
    
    def verify(self, password: str, password_hash: str) -> bool:
        """Verify password against hash
        
        Args:
            password: Plain text password
            password_hash: Stored hash
            
        Returns:
            True if password matches hash
        """
        ...
    
    def generate_temporary(self) -> str:
        """Generate temporary password for invites
        
        Returns:
            Random password meeting requirements
        """
        ...
    
    def strength_score(self, password: str) -> int:
        """Calculate password strength score
        
        Args:
            password: Plain text password
            
        Returns:
            Score 0-100 (weak to strong)
        """
        ...
