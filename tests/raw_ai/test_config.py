"""Tests for raw_ai configuration."""

import os
from unittest.mock import patch

from raw_ai.config import (
    AIConfig,
    API_KEY_ENV_VARS,
    DEFAULT_MODELS,
    get_api_key,
    get_model,
)


class TestAIConfig:
    """Tests for AIConfig model."""

    def test_default_values(self) -> None:
        config = AIConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.api_key is None
        assert config.temperature == 0.7

    def test_custom_values(self) -> None:
        config = AIConfig(
            provider="anthropic",
            model="claude-3-5-sonnet-latest",
            temperature=0.5,
        )
        assert config.provider == "anthropic"
        assert config.model == "claude-3-5-sonnet-latest"
        assert config.temperature == 0.5

    def test_temperature_bounds(self) -> None:
        config = AIConfig(temperature=0.0)
        assert config.temperature == 0.0

        config = AIConfig(temperature=2.0)
        assert config.temperature == 2.0


class TestGetApiKey:
    """Tests for get_api_key function."""

    def test_openai_key(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
            key = get_api_key("openai")
            assert key == "sk-test123"

    def test_anthropic_key(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            key = get_api_key("anthropic")
            assert key == "sk-ant-test"

    def test_missing_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            key = get_api_key("openai")
            assert key is None

    def test_ollama_no_key_needed(self) -> None:
        key = get_api_key("ollama")
        assert key is None


class TestGetModel:
    """Tests for get_model function."""

    def test_default_model(self) -> None:
        model_str = get_model()
        assert model_str == "openai:gpt-4o-mini"

    def test_explicit_openai(self) -> None:
        model_str = get_model(model="gpt-4o")
        assert model_str == "openai:gpt-4o"

    def test_explicit_anthropic(self) -> None:
        model_str = get_model(model="claude-3-5-sonnet-latest")
        assert model_str == "anthropic:claude-3-5-sonnet-latest"

    def test_explicit_groq(self) -> None:
        model_str = get_model(model="llama-3.1-70b-versatile")
        assert model_str == "groq:llama-3.1-70b-versatile"

    def test_explicit_provider(self) -> None:
        model_str = get_model(provider="anthropic")
        assert model_str == "anthropic:claude-3-5-sonnet-latest"

    def test_o1_model(self) -> None:
        model_str = get_model(model="o1-preview")
        assert model_str == "openai:o1-preview"

    def test_mixtral_model(self) -> None:
        model_str = get_model(model="mixtral-8x7b")
        assert model_str == "groq:mixtral-8x7b"


class TestConstants:
    """Tests for module constants."""

    def test_default_models_has_providers(self) -> None:
        assert "openai" in DEFAULT_MODELS
        assert "anthropic" in DEFAULT_MODELS
        assert "groq" in DEFAULT_MODELS
        assert "ollama" in DEFAULT_MODELS

    def test_api_key_env_vars(self) -> None:
        assert API_KEY_ENV_VARS["openai"] == "OPENAI_API_KEY"
        assert API_KEY_ENV_VARS["anthropic"] == "ANTHROPIC_API_KEY"
        assert API_KEY_ENV_VARS["groq"] == "GROQ_API_KEY"
