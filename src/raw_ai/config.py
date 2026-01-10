"""AI model configuration for RAW workflows."""

import os
from typing import Literal

from pydantic import BaseModel, Field

ModelProvider = Literal["openai", "anthropic", "groq", "ollama"]


class AIConfig(BaseModel):
    """Configuration for AI model access."""

    provider: ModelProvider = Field(default="openai")
    model: str = Field(default="gpt-4o-mini")
    api_key: str | None = Field(default=None)
    base_url: str | None = Field(default=None)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None)
    timeout: float = Field(default=30.0)


# Default model mappings
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "groq": "llama-3.1-70b-versatile",
    "ollama": "llama3.2",
}

# Environment variable names for API keys
API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "groq": "GROQ_API_KEY",
}


def get_api_key(provider: ModelProvider) -> str | None:
    """Get API key from environment for the given provider."""
    env_var = API_KEY_ENV_VARS.get(provider)
    if env_var:
        return os.environ.get(env_var)
    return None


def get_model(
    model: str | None = None,
    provider: ModelProvider | None = None,
    **kwargs,
) -> "Agent":
    """Get a PydanticAI model instance.

    Args:
        model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet-latest")
        provider: Provider name (inferred from model if not specified)
        **kwargs: Additional config options

    Returns:
        Configured PydanticAI Agent
    """

    if provider is None:
        if model is None:
            provider = "openai"
            model = DEFAULT_MODELS[provider]
        elif model.startswith("gpt") or model.startswith("o1"):
            provider = "openai"
        elif model.startswith("claude"):
            provider = "anthropic"
        elif model.startswith("llama") or model.startswith("mixtral"):
            provider = "groq"
        else:
            provider = "openai"

    if model is None:
        model = DEFAULT_MODELS.get(provider, "gpt-4o-mini")

    # Build model string for PydanticAI
    if provider == "openai":
        model_str = f"openai:{model}"
    elif provider == "anthropic":
        model_str = f"anthropic:{model}"
    elif provider == "groq":
        model_str = f"groq:{model}"
    elif provider == "ollama":
        model_str = f"ollama:{model}"
    else:
        model_str = model

    return model_str
