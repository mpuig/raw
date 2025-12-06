"""Tests for secret provider abstraction."""

import pytest

from raw_runtime.secrets import (
    CachingSecretProvider,
    ChainedSecretProvider,
    DotEnvSecretProvider,
    EnvVarSecretProvider,
    SecretProvider,
    get_secret,
    get_secret_provider,
    require_secret,
    set_secret_provider,
)


class TestSecretProviderProtocol:
    """Test that implementations satisfy the SecretProvider protocol."""

    def test_env_var_provider_is_secret_provider(self):
        assert isinstance(EnvVarSecretProvider(), SecretProvider)

    def test_dotenv_provider_is_secret_provider(self):
        assert isinstance(DotEnvSecretProvider(), SecretProvider)

    def test_chained_provider_is_secret_provider(self):
        assert isinstance(ChainedSecretProvider([]), SecretProvider)

    def test_caching_provider_is_secret_provider(self):
        assert isinstance(
            CachingSecretProvider(EnvVarSecretProvider()),
            SecretProvider,
        )


class TestEnvVarSecretProvider:
    """Tests for EnvVarSecretProvider."""

    @pytest.fixture
    def provider(self):
        return EnvVarSecretProvider()

    def test_get_existing_secret(self, provider, monkeypatch):
        monkeypatch.setenv("TEST_SECRET", "secret_value")
        assert provider.get_secret("TEST_SECRET") == "secret_value"

    def test_get_missing_secret_returns_none(self, provider, monkeypatch):
        monkeypatch.delenv("MISSING_SECRET", raising=False)
        assert provider.get_secret("MISSING_SECRET") is None

    def test_get_missing_secret_returns_default(self, provider, monkeypatch):
        monkeypatch.delenv("MISSING_SECRET", raising=False)
        assert provider.get_secret("MISSING_SECRET", "default") == "default"

    def test_has_secret_true(self, provider, monkeypatch):
        monkeypatch.setenv("EXISTING", "value")
        assert provider.has_secret("EXISTING") is True

    def test_has_secret_false(self, provider, monkeypatch):
        monkeypatch.delenv("NONEXISTENT", raising=False)
        assert provider.has_secret("NONEXISTENT") is False

    def test_require_secret_exists(self, provider, monkeypatch):
        monkeypatch.setenv("REQUIRED", "important_value")
        assert provider.require_secret("REQUIRED") == "important_value"

    def test_require_secret_missing_raises(self, provider, monkeypatch):
        monkeypatch.delenv("MISSING_REQUIRED", raising=False)
        with pytest.raises(KeyError, match="Secret not found"):
            provider.require_secret("MISSING_REQUIRED")


class TestDotEnvSecretProvider:
    """Tests for DotEnvSecretProvider."""

    def test_loads_from_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("MY_SECRET=from_file\nANOTHER=value2")

        provider = DotEnvSecretProvider(search_path=tmp_path)
        assert provider.get_secret("MY_SECRET") == "from_file"
        assert provider.get_secret("ANOTHER") == "value2"

    def test_env_var_takes_precedence(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("MY_SECRET=from_file")
        monkeypatch.setenv("MY_SECRET", "from_env")

        provider = DotEnvSecretProvider(search_path=tmp_path)
        assert provider.get_secret("MY_SECRET") == "from_env"

    def test_handles_quoted_values(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("SINGLE='single quotes'\nDOUBLE=\"double quotes\"")

        provider = DotEnvSecretProvider(search_path=tmp_path)
        assert provider.get_secret("SINGLE") == "single quotes"
        assert provider.get_secret("DOUBLE") == "double quotes"

    def test_skips_comments_and_empty_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# Comment\n\nVALID=yes\n# Another comment")

        provider = DotEnvSecretProvider(search_path=tmp_path)
        assert provider.get_secret("VALID") == "yes"

    def test_returns_none_if_no_env_file(self, tmp_path):
        provider = DotEnvSecretProvider(search_path=tmp_path)
        assert provider.get_secret("ANYTHING") is None

    def test_searches_parent_directories(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("PARENT_SECRET=found")

        subdir = tmp_path / "sub" / "dir"
        subdir.mkdir(parents=True)

        provider = DotEnvSecretProvider(search_path=subdir)
        assert provider.get_secret("PARENT_SECRET") == "found"


class TestChainedSecretProvider:
    """Tests for ChainedSecretProvider."""

    def test_empty_chain(self):
        provider = ChainedSecretProvider([])
        assert provider.get_secret("ANY") is None
        assert provider.has_secret("ANY") is False

    def test_first_provider_wins(self, monkeypatch):
        monkeypatch.setenv("SHARED", "from_env")

        env = EnvVarSecretProvider()

        class MockProvider:
            def get_secret(self, key, default=None):
                return "from_mock" if key == "SHARED" else default

            def has_secret(self, key):
                return key == "SHARED"

            def require_secret(self, key):
                if key == "SHARED":
                    return "from_mock"
                raise KeyError(key)

        provider = ChainedSecretProvider([env, MockProvider()])
        assert provider.get_secret("SHARED") == "from_env"

    def test_falls_through_to_second(self, monkeypatch):
        monkeypatch.delenv("ONLY_IN_MOCK", raising=False)

        class MockProvider:
            def get_secret(self, key, default=None):
                return "mock_value" if key == "ONLY_IN_MOCK" else default

            def has_secret(self, key):
                return key == "ONLY_IN_MOCK"

            def require_secret(self, key):
                if key == "ONLY_IN_MOCK":
                    return "mock_value"
                raise KeyError(key)

        provider = ChainedSecretProvider([EnvVarSecretProvider(), MockProvider()])
        assert provider.get_secret("ONLY_IN_MOCK") == "mock_value"

    def test_require_from_chain(self, monkeypatch):
        monkeypatch.setenv("CHAINED", "value")
        provider = ChainedSecretProvider([EnvVarSecretProvider()])
        assert provider.require_secret("CHAINED") == "value"

    def test_require_not_found_raises(self, monkeypatch):
        monkeypatch.delenv("MISSING", raising=False)
        provider = ChainedSecretProvider([EnvVarSecretProvider()])
        with pytest.raises(KeyError, match="Secret not found"):
            provider.require_secret("MISSING")


class TestCachingSecretProvider:
    """Tests for CachingSecretProvider."""

    def test_caches_value(self, monkeypatch):
        monkeypatch.setenv("CACHED", "original")
        inner = EnvVarSecretProvider()
        provider = CachingSecretProvider(inner)

        # First call
        assert provider.get_secret("CACHED") == "original"

        # Change env var
        monkeypatch.setenv("CACHED", "changed")

        # Should still return cached value
        assert provider.get_secret("CACHED") == "original"

    def test_caches_none_values(self, monkeypatch):
        monkeypatch.delenv("MISSING", raising=False)
        inner = EnvVarSecretProvider()
        provider = CachingSecretProvider(inner)

        # First call returns None
        assert provider.get_secret("MISSING") is None

        # Add the env var
        monkeypatch.setenv("MISSING", "now_exists")

        # Should still return default (None was cached)
        assert provider.get_secret("MISSING", "default") == "default"

    def test_clear_cache(self, monkeypatch):
        monkeypatch.setenv("CLEARABLE", "first")
        inner = EnvVarSecretProvider()
        provider = CachingSecretProvider(inner)

        assert provider.get_secret("CLEARABLE") == "first"

        monkeypatch.setenv("CLEARABLE", "second")
        provider.clear_cache()

        assert provider.get_secret("CLEARABLE") == "second"

    def test_has_secret_uses_cache(self, monkeypatch):
        monkeypatch.setenv("EXISTS", "yes")
        inner = EnvVarSecretProvider()
        provider = CachingSecretProvider(inner)

        # Populate cache
        provider.get_secret("EXISTS")
        monkeypatch.delenv("EXISTS")

        # Should still report exists from cache
        assert provider.has_secret("EXISTS") is True


class TestGlobalSecretProvider:
    """Tests for global secret provider functions."""

    def test_default_provider_is_chained(self):
        set_secret_provider(None)
        provider = get_secret_provider()
        assert isinstance(provider, ChainedSecretProvider)

    def test_set_and_get_provider(self):
        custom = EnvVarSecretProvider()
        set_secret_provider(custom)
        assert get_secret_provider() is custom
        set_secret_provider(None)

    def test_get_secret_convenience(self, monkeypatch):
        monkeypatch.setenv("CONVENIENT", "easy")
        set_secret_provider(None)
        assert get_secret("CONVENIENT") == "easy"

    def test_require_secret_convenience(self, monkeypatch):
        monkeypatch.setenv("REQUIRED_CONV", "needed")
        set_secret_provider(None)
        assert require_secret("REQUIRED_CONV") == "needed"

    def test_require_secret_raises(self, monkeypatch):
        monkeypatch.delenv("NOT_THERE", raising=False)
        set_secret_provider(None)
        with pytest.raises(KeyError):
            require_secret("NOT_THERE")
