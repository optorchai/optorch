"""Pricing models for LLM cost tracking - hardcoded defaults, no external files"""
from pydantic import BaseModel, Field
from typing import Dict


class ModelPricingConfig(BaseModel):
    """Pricing for a single model (per 1M tokens)"""
    input: float = Field(ge=0, description="Input token cost per 1M tokens")
    output: float = Field(ge=0, description="Output token cost per 1M tokens")


class CostsConfig(BaseModel):
    """LLM pricing with hardcoded defaults for common models"""
    currency: str = Field(default="USD", description="Currency for all pricing")
    pricing: Dict[str, ModelPricingConfig] = Field(
        default={
            "gpt-4o": ModelPricingConfig(input=2.50, output=10.00),
            "gpt-4o-mini": ModelPricingConfig(input=0.15, output=0.60),
            "gpt-4-turbo": ModelPricingConfig(input=10.00, output=30.00),
            "gpt-3.5-turbo": ModelPricingConfig(input=0.50, output=1.50),
            "groq/llama-3.3-70b-versatile": ModelPricingConfig(input=0.59, output=0.79),
            "groq/llama-3.1-70b-versatile": ModelPricingConfig(input=0.59, output=0.79),
            "groq/llama-3.1-8b-instant": ModelPricingConfig(input=0.05, output=0.08),
            "ollama": ModelPricingConfig(input=0.0, output=0.0),
            "text-embedding-3-small": ModelPricingConfig(input=0.02, output=0.0),
            "text-embedding-3-large": ModelPricingConfig(input=0.13, output=0.0),
            "text-embedding-ada-002": ModelPricingConfig(input=0.10, output=0.0),
        },
        description="Model pricing per 1M tokens"
    )
    
    model_config = {"extra": "allow"}
