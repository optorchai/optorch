from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class NISTPasswordConfig(BaseModel):
    """config for nist 800-63b password provider"""
    
    min_length: int = Field(default=12, ge=8, le=128, description="min password length")
    max_length: int = Field(default=64, ge=8, le=1024, description="max password length")
    bcrypt_rounds: int = Field(default=14, ge=4, le=31, description="bcrypt cost factor")
    common_passwords_file: Optional[str] = Field(default=None, description="path to custom common passwords list")
    wordlist_file: Optional[str] = Field(default=None, description="path to custom wordlist for passphrase generation")
    
    @field_validator("max_length")
    @classmethod
    def validate_length_range(cls, v: int, info) -> int:
        """ensure max > min"""
        if "min_length" in info.data and v < info.data["min_length"]:
            raise ValueError(f"max_length ({v}) must be >= min_length ({info.data['min_length']})")
        return v


class EnterprisePasswordConfig(BaseModel):
    """config for enterprise password provider with composition rules"""
    
    min_length: int = Field(default=14, ge=8, le=128, description="min password length")
    max_length: int = Field(default=128, ge=8, le=1024, description="max password length")
    require_uppercase: bool = Field(default=True, description="require uppercase letters")
    require_lowercase: bool = Field(default=True, description="require lowercase letters")
    require_digit: bool = Field(default=True, description="require digits")
    require_special: bool = Field(default=True, description="require special characters")
    special_chars: str = Field(default="!@#$%^&*()_+-=[]{}|;:,.<>?", description="allowed special characters")
    max_consecutive_chars: int = Field(default=3, ge=1, le=10, description="max consecutive identical chars")
    bcrypt_rounds: int = Field(default=14, ge=4, le=31, description="bcrypt cost factor")
    
    @field_validator("max_length")
    @classmethod
    def validate_length_range(cls, v: int, info) -> int:
        """ensure max > min"""
        if "min_length" in info.data and v < info.data["min_length"]:
            raise ValueError(
                f"max_length ({v}) must be >= min_length ({info.data['min_length']})"
            )
        return v
    
    @field_validator("special_chars")
    @classmethod
    def validate_special_chars(cls, v: str) -> str:
        """ensure at least one special char defined"""
        if not v:
            raise ValueError("special_chars cannot be empty")
        return v


class Argon2PasswordConfig(BaseModel):
    """config for argon2id password provider (memory-hard hashing)"""
    
    min_length: int = Field(default=12, ge=8, le=128, description="min password length")
    max_length: int = Field(default=128, ge=8, le=1024, description="max password length")
    time_cost: int = Field(default=3, ge=1, le=10, description="iterations")
    memory_cost: int = Field(default=65536, ge=1024, le=1048576, description="memory in KiB (64 MiB default)")
    parallelism: int = Field(default=4, ge=1, le=16, description="threads")
    hash_len: int = Field(default=32, ge=16, le=64, description="hash output length")
    salt_len: int = Field(default=16, ge=8, le=32, description="salt length")
    
    @field_validator("max_length")
    @classmethod
    def validate_length_range(cls, v: int, info) -> int:
        """ensure max > min"""
        if "min_length" in info.data and v < info.data["min_length"]:
            raise ValueError(
                f"max_length ({v}) must be >= min_length ({info.data['min_length']})"
            )
        return v


class PasswordManagerConfig(BaseModel):
    """config for password manager with provider selection"""
    
    provider: Literal["nist", "enterprise", "argon2"] = Field(default="nist", description="password provider type")
    nist: NISTPasswordConfig = Field(default_factory=NISTPasswordConfig, description="nist provider config")
    enterprise: EnterprisePasswordConfig = Field(default_factory=EnterprisePasswordConfig, description="enterprise provider config")
    argon2: Argon2PasswordConfig = Field(default_factory=Argon2PasswordConfig, description="argon2 provider config")
