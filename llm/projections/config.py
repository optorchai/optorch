"""cost projection configuration"""
from pydantic import BaseModel, Field


class CostProjectionConfig(BaseModel):
    """cost projection defaults with override support"""
    
    default_output_tokens: dict[str, int] = Field(
        default_factory=lambda: {
            "gpt-4": 50,
            "gpt-3.5": 50,
            "claude": 60,
            "llama": 40,
            "groq": 40,
        },
        description="default output token estimates by model family pattern"
    )
    
    fallback_output_tokens: int = Field(
        default=50,
        description="fallback when no pattern matches"
    )
