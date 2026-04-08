"""Tests for nats_core.config — NATSConfig pydantic-settings model."""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings

from nats_core.config import NATSConfig

# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestNATSConfigSmoke:
    """Core happy-path scenarios for NATSConfig."""

    def test_nats_config_is_base_settings_subclass(self) -> None:
        """NATSConfig must inherit from pydantic-settings BaseSettings."""
        assert issubclass(NATSConfig, BaseSettings)

    def test_nats_config_instantiates_with_defaults(self) -> None:
        """NATSConfig can be instantiated without any arguments."""
        cfg = NATSConfig()
        assert isinstance(cfg, NATSConfig)

    def test_nats_config_has_model_config(self) -> None:
        """NATSConfig must define model_config with env_prefix and env_file."""
        mc = NATSConfig.model_config
        assert mc.get("env_prefix") == "NATS_"
        assert mc.get("env_file") == ".env"

    def test_default_configuration_connects_to_localhost(self) -> None:
        """Scenario: Default configuration connects to localhost."""
        cfg = NATSConfig()
        assert cfg.url == "nats://localhost:4222"
        assert cfg.connect_timeout == 5.0
        assert cfg.reconnect_time_wait == 2.0
        assert cfg.max_reconnect_attempts == 60
        assert cfg.name == "nats-core-client"

    def test_environment_variable_overrides_default_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Scenario: Environment variable overrides the default URL."""
        monkeypatch.setenv("NATS_URL", "nats://custom-host:4222")
        cfg = NATSConfig()
        assert cfg.url == "nats://custom-host:4222"

    def test_constructor_arguments_override_defaults(self) -> None:
        """Scenario: Constructor arguments override defaults."""
        cfg = NATSConfig(
            url="tls://secure-host:4222",
            connect_timeout=10.0,
            reconnect_time_wait=5.0,
            max_reconnect_attempts=100,
            name="my-custom-client",
        )
        assert cfg.url == "tls://secure-host:4222"
        assert cfg.connect_timeout == 10.0
        assert cfg.reconnect_time_wait == 5.0
        assert cfg.max_reconnect_attempts == 100
        assert cfg.name == "my-custom-client"


# ---------------------------------------------------------------------------
# Key example tests
# ---------------------------------------------------------------------------


@pytest.mark.key_example
class TestNATSConfigExport:
    """NATSConfig is publicly exported from the package."""

    def test_nats_config_importable_from_package(self) -> None:
        """NATSConfig should be importable directly from nats_core."""
        from nats_core import NATSConfig as Imported

        assert Imported is NATSConfig

    def test_nats_config_in_all(self) -> None:
        """NATSConfig must appear in nats_core.__all__."""
        import nats_core

        assert "NATSConfig" in nats_core.__all__


# ---------------------------------------------------------------------------
# Key example: env-var bindings
# ---------------------------------------------------------------------------


@pytest.mark.key_example
class TestNATSConfigEnvBindings:
    """Each field is bound to the correct NATS_ environment variable."""

    def test_connect_timeout_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NATS_CONNECT_TIMEOUT overrides the connect_timeout default."""
        monkeypatch.setenv("NATS_CONNECT_TIMEOUT", "15.5")
        cfg = NATSConfig()
        assert cfg.connect_timeout == 15.5

    def test_reconnect_time_wait_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NATS_RECONNECT_TIME_WAIT overrides the reconnect_time_wait default."""
        monkeypatch.setenv("NATS_RECONNECT_TIME_WAIT", "8.0")
        cfg = NATSConfig()
        assert cfg.reconnect_time_wait == 8.0

    def test_max_reconnect_attempts_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NATS_MAX_RECONNECT_ATTEMPTS overrides the max_reconnect_attempts default."""
        monkeypatch.setenv("NATS_MAX_RECONNECT_ATTEMPTS", "200")
        cfg = NATSConfig()
        assert cfg.max_reconnect_attempts == 200

    def test_name_env_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NATS_NAME overrides the name default."""
        monkeypatch.setenv("NATS_NAME", "my-agent")
        cfg = NATSConfig()
        assert cfg.name == "my-agent"


# ---------------------------------------------------------------------------
# Boundary / edge-case tests
# ---------------------------------------------------------------------------


@pytest.mark.boundary
class TestNATSConfigBoundary:
    """Boundary and structural checks."""

    def test_model_config_is_settings_config_dict(self) -> None:
        """model_config should be a SettingsConfigDict (or compatible mapping)."""
        mc = NATSConfig.model_config
        # SettingsConfigDict is a TypedDict at runtime; just verify it's a dict
        assert isinstance(mc, dict)

    def test_module_has_future_annotations(self) -> None:
        """config.py must use `from __future__ import annotations`."""
        import nats_core.config as mod

        assert hasattr(mod, "__annotations__") or True  # import succeeds → future ok
        # More concrete: check the source
        import inspect

        source = inspect.getsource(mod)
        assert "from __future__ import annotations" in source

    def test_module_has_google_style_docstring(self) -> None:
        """config module must have a module-level docstring."""
        import nats_core.config as mod

        assert mod.__doc__ is not None
        assert len(mod.__doc__.strip()) > 0

    def test_connect_timeout_at_zero_is_accepted(self) -> None:
        """Scenario: Connect timeout at zero is accepted."""
        cfg = NATSConfig(connect_timeout=0.0)
        assert cfg.connect_timeout == 0.0

    def test_reconnect_time_wait_at_zero_is_accepted(self) -> None:
        """Scenario: Reconnect time wait at zero is accepted."""
        cfg = NATSConfig(reconnect_time_wait=0.0)
        assert cfg.reconnect_time_wait == 0.0

    def test_max_reconnect_attempts_at_zero_means_no_retries(self) -> None:
        """Scenario: Max reconnect attempts at zero means no retries."""
        cfg = NATSConfig(max_reconnect_attempts=0)
        assert cfg.max_reconnect_attempts == 0

    def test_tls_scheme_is_accepted(self) -> None:
        """URL with tls:// scheme should be accepted."""
        cfg = NATSConfig(url="tls://secure-host:4222")
        assert cfg.url == "tls://secure-host:4222"

    def test_all_fields_have_descriptions(self) -> None:
        """All fields must carry Field(description=...) per project model pattern."""
        for field_name, field_info in NATSConfig.model_fields.items():
            assert field_info.description is not None, (
                f"Field '{field_name}' is missing a description"
            )
            assert len(field_info.description) > 0, (
                f"Field '{field_name}' has an empty description"
            )


# ---------------------------------------------------------------------------
# Negative tests
# ---------------------------------------------------------------------------


@pytest.mark.negative
class TestNATSConfigNegative:
    """Invalid input and error-path tests."""

    def test_negative_connect_timeout_is_rejected(self) -> None:
        """Scenario: Negative connect timeout is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(connect_timeout=-1.0)
        assert "connect_timeout" in str(exc_info.value)

    def test_negative_reconnect_time_wait_is_rejected(self) -> None:
        """Scenario: Negative reconnect time wait is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(reconnect_time_wait=-0.1)
        assert "reconnect_time_wait" in str(exc_info.value)

    def test_negative_max_reconnect_attempts_is_rejected(self) -> None:
        """Scenario: Negative max reconnect attempts is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(max_reconnect_attempts=-1)
        assert "max_reconnect_attempts" in str(exc_info.value)

    def test_invalid_url_scheme_is_rejected(self) -> None:
        """Scenario: Invalid URL scheme is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(url="http://localhost:4222")
        assert "url" in str(exc_info.value).lower()

    def test_empty_url_is_rejected(self) -> None:
        """Scenario: Empty URL is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(url="")
        assert "url" in str(exc_info.value).lower()

    def test_empty_client_name_is_rejected(self) -> None:
        """Scenario: Empty client name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(name="")
        assert "name" in str(exc_info.value).lower()

    def test_blank_client_name_is_rejected(self) -> None:
        """Blank (whitespace-only) client name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(name="   ")
        assert "name" in str(exc_info.value).lower()

    def test_websocket_url_scheme_is_rejected(self) -> None:
        """ws:// scheme is not a valid NATS URL."""
        with pytest.raises(ValidationError):
            NATSConfig(url="ws://localhost:4222")

    def test_ftp_url_scheme_is_rejected(self) -> None:
        """ftp:// scheme is not a valid NATS URL."""
        with pytest.raises(ValidationError):
            NATSConfig(url="ftp://localhost:4222")


# ---------------------------------------------------------------------------
# Auth fields — smoke / happy-path
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestNATSConfigAuthSmoke:
    """Auth fields default to None and accept valid values."""

    def test_auth_fields_default_to_none(self) -> None:
        """All auth fields default to None when not provided."""
        cfg = NATSConfig()
        assert cfg.user is None
        assert cfg.password is None
        assert cfg.creds_file is None

    def test_user_and_password_accepted_together(self) -> None:
        """Scenario: Configuring user and password authentication."""
        cfg = NATSConfig(user="admin", password="s3cret")
        assert cfg.user == "admin"
        assert isinstance(cfg.password, SecretStr)
        assert cfg.password.get_secret_value() == "s3cret"

    def test_creds_file_accepted_alone(self) -> None:
        """Scenario: Configuring NKey credentials file."""
        cfg = NATSConfig(creds_file="/etc/nats/nkey.creds")
        assert cfg.creds_file == "/etc/nats/nkey.creds"


# ---------------------------------------------------------------------------
# Auth fields — key-example env-var bindings
# ---------------------------------------------------------------------------


@pytest.mark.key_example
class TestNATSConfigAuthEnvBindings:
    """Auth fields are bound to NATS_ environment variables."""

    def test_user_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario: Configuring user and password authentication from environment."""
        monkeypatch.setenv("NATS_USER", "env-user")
        monkeypatch.setenv("NATS_PASSWORD", "env-pass")
        cfg = NATSConfig()
        assert cfg.user == "env-user"
        assert cfg.password is not None
        assert cfg.password.get_secret_value() == "env-pass"

    def test_creds_file_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Scenario: Configuring NKey credentials file from environment."""
        monkeypatch.setenv("NATS_CREDS_FILE", "/tmp/nats.creds")
        cfg = NATSConfig()
        assert cfg.creds_file == "/tmp/nats.creds"


# ---------------------------------------------------------------------------
# Auth fields — boundary / edge-case
# ---------------------------------------------------------------------------


@pytest.mark.boundary
class TestNATSConfigAuthBoundary:
    """Boundary and structural checks for auth fields."""

    def test_auth_fields_have_descriptions(self) -> None:
        """All auth fields must carry Field(description=...) metadata."""
        auth_fields = ("user", "password", "creds_file")
        for field_name in auth_fields:
            field_info = NATSConfig.model_fields[field_name]
            assert field_info.description is not None, (
                f"Field '{field_name}' is missing a description"
            )
            assert len(field_info.description) > 0, (
                f"Field '{field_name}' has an empty description"
            )

    def test_password_is_secret_str_type(self) -> None:
        """password field should use SecretStr for automatic masking."""
        cfg = NATSConfig(user="u", password="p")
        assert isinstance(cfg.password, SecretStr)

    def test_password_masked_in_repr(self) -> None:
        """Scenario: Sensitive fields are masked in string representation."""
        cfg = NATSConfig(user="u", password="super-secret")
        text = repr(cfg)
        assert "super-secret" not in text

    def test_password_not_exposed_in_model_dump(self) -> None:
        """Scenario: Password is not exposed when config is serialised to dict."""
        cfg = NATSConfig(user="u", password="super-secret")
        dumped = cfg.model_dump()
        # SecretStr serialises as '**********' by default
        assert dumped["password"] != "super-secret"

    def test_creds_file_simple_filename_accepted(self) -> None:
        """A simple filename without path traversal should be accepted."""
        cfg = NATSConfig(creds_file="nats.creds")
        assert cfg.creds_file == "nats.creds"

    def test_creds_file_absolute_path_accepted(self) -> None:
        """An absolute path without traversal should be accepted."""
        cfg = NATSConfig(creds_file="/var/nats/credentials.creds")
        assert cfg.creds_file == "/var/nats/credentials.creds"


# ---------------------------------------------------------------------------
# Auth fields — negative tests
# ---------------------------------------------------------------------------


@pytest.mark.negative
class TestNATSConfigAuthNegative:
    """Invalid auth configurations are rejected."""

    def test_user_without_password_is_rejected(self) -> None:
        """Scenario: User without password is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(user="admin")
        errors = str(exc_info.value)
        assert "password" in errors.lower() or "user" in errors.lower()

    def test_password_without_user_is_rejected(self) -> None:
        """Scenario: Password without user is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(password="s3cret")
        errors = str(exc_info.value)
        assert "password" in errors.lower() or "user" in errors.lower()

    def test_password_and_creds_file_together_is_rejected(self) -> None:
        """Scenario: Providing both password auth and creds file is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(user="admin", password="s3cret", creds_file="/tmp/nats.creds")
        errors = str(exc_info.value)
        assert "password" in errors.lower() or "creds_file" in errors.lower()

    def test_creds_file_with_path_traversal_is_rejected(self) -> None:
        """Scenario: Creds file with path traversal is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(creds_file="../../../etc/passwd")
        assert "creds_file" in str(exc_info.value).lower() or ".." in str(exc_info.value)

    def test_creds_file_with_embedded_traversal_is_rejected(self) -> None:
        """Path traversal embedded within a path is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            NATSConfig(creds_file="/var/nats/../../etc/passwd")
        assert ".." in str(exc_info.value)

    def test_creds_file_with_middle_traversal_is_rejected(self) -> None:
        """Path traversal in the middle of a path is rejected."""
        with pytest.raises(ValidationError):
            NATSConfig(creds_file="subdir/../secret.creds")


# ---------------------------------------------------------------------------
# to_connect_kwargs() — smoke / happy-path
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestToConnectKwargsSmoke:
    """Core happy-path scenarios for to_connect_kwargs()."""

    def test_to_connect_kwargs_returns_dict(self) -> None:
        """to_connect_kwargs() must return a plain dict."""
        cfg = NATSConfig()
        result = cfg.to_connect_kwargs()
        assert isinstance(result, dict)

    def test_default_config_kwargs_contain_servers_as_list(self) -> None:
        """Scenario: Config produces valid nats-py connection kwargs (servers)."""
        cfg = NATSConfig()
        kwargs = cfg.to_connect_kwargs()
        assert kwargs["servers"] == ["nats://localhost:4222"]

    def test_default_config_kwargs_contain_connect_timeout(self) -> None:
        """Default config kwargs include connect_timeout."""
        cfg = NATSConfig()
        kwargs = cfg.to_connect_kwargs()
        assert kwargs["connect_timeout"] == 5.0

    def test_default_config_kwargs_contain_reconnect_time_wait(self) -> None:
        """Default config kwargs include reconnect_time_wait."""
        cfg = NATSConfig()
        kwargs = cfg.to_connect_kwargs()
        assert kwargs["reconnect_time_wait"] == 2.0

    def test_default_config_kwargs_contain_max_reconnect_attempts(self) -> None:
        """Default config kwargs include max_reconnect_attempts."""
        cfg = NATSConfig()
        kwargs = cfg.to_connect_kwargs()
        assert kwargs["max_reconnect_attempts"] == 60

    def test_default_config_kwargs_contain_name(self) -> None:
        """Default config kwargs include name."""
        cfg = NATSConfig()
        kwargs = cfg.to_connect_kwargs()
        assert kwargs["name"] == "nats-core-client"


# ---------------------------------------------------------------------------
# to_connect_kwargs() — key-example tests
# ---------------------------------------------------------------------------


@pytest.mark.key_example
class TestToConnectKwargsKeyExample:
    """Key usage examples for to_connect_kwargs()."""

    def test_kwargs_with_user_password_auth(self) -> None:
        """Scenario: Config with user/password produces kwargs with auth fields."""
        cfg = NATSConfig(user="admin", password="s3cret")
        kwargs = cfg.to_connect_kwargs()
        assert kwargs["user"] == "admin"
        assert kwargs["password"] == "s3cret"

    def test_kwargs_with_creds_file(self) -> None:
        """Scenario: Config with creds_file produces kwargs with credentials."""
        cfg = NATSConfig(creds_file="/etc/nats/nkey.creds")
        kwargs = cfg.to_connect_kwargs()
        assert kwargs["credentials"] == "/etc/nats/nkey.creds"


# ---------------------------------------------------------------------------
# to_connect_kwargs() — edge-case tests
# ---------------------------------------------------------------------------


@pytest.mark.edge_case
class TestToConnectKwargsEdgeCase:
    """Edge-case scenarios for to_connect_kwargs()."""

    def test_kwargs_without_auth_excludes_user_and_password(self) -> None:
        """When no auth is configured, user/password keys are absent."""
        cfg = NATSConfig()
        kwargs = cfg.to_connect_kwargs()
        assert "user" not in kwargs
        assert "password" not in kwargs

    def test_kwargs_without_creds_excludes_credentials(self) -> None:
        """When no creds_file is configured, credentials key is absent."""
        cfg = NATSConfig()
        kwargs = cfg.to_connect_kwargs()
        assert "credentials" not in kwargs

    def test_kwargs_password_is_raw_string_not_secret_str(self) -> None:
        """to_connect_kwargs() must unwrap SecretStr to plain string for nats-py."""
        cfg = NATSConfig(user="u", password="raw-value")
        kwargs = cfg.to_connect_kwargs()
        assert isinstance(kwargs["password"], str)
        assert kwargs["password"] == "raw-value"

    def test_kwargs_with_custom_url(self) -> None:
        """Custom URL is wrapped in a single-element list."""
        cfg = NATSConfig(url="tls://secure-host:4222")
        kwargs = cfg.to_connect_kwargs()
        assert kwargs["servers"] == ["tls://secure-host:4222"]

    def test_kwargs_complete_structure_with_auth(self) -> None:
        """Full kwargs structure with all expected keys when auth is set."""
        cfg = NATSConfig(
            url="nats://prod:4222",
            connect_timeout=10.0,
            reconnect_time_wait=5.0,
            max_reconnect_attempts=100,
            name="my-client",
            user="admin",
            password="s3cret",
        )
        kwargs = cfg.to_connect_kwargs()
        assert kwargs == {
            "servers": ["nats://prod:4222"],
            "connect_timeout": 10.0,
            "reconnect_time_wait": 5.0,
            "max_reconnect_attempts": 100,
            "name": "my-client",
            "user": "admin",
            "password": "s3cret",
        }


# ---------------------------------------------------------------------------
# Serialisation masking — edge-case tests (BDD scenarios)
# ---------------------------------------------------------------------------


@pytest.mark.edge_case
class TestSerialisationMasking:
    """BDD scenarios for sensitive field masking in serialisation."""

    def test_model_dump_password_is_masked(self) -> None:
        """Scenario: Password is not exposed when config is serialised to dict."""
        cfg = NATSConfig(user="admin", password="super-secret")
        dumped = cfg.model_dump()
        assert "super-secret" not in str(dumped)

    def test_repr_password_is_masked(self) -> None:
        """Scenario: Sensitive fields are masked in string representation."""
        cfg = NATSConfig(user="admin", password="super-secret")
        text = repr(cfg)
        assert "super-secret" not in text

    def test_str_password_is_masked(self) -> None:
        """Scenario: Sensitive fields are masked in str() output."""
        cfg = NATSConfig(user="admin", password="super-secret")
        text = str(cfg)
        assert "super-secret" not in text


# ---------------------------------------------------------------------------
# Integration test — nats-py Client.connect() compatibility
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestToConnectKwargsIntegration:
    """Integration test verifying kwargs are accepted by nats-py Client.connect()."""

    def test_kwargs_accepted_by_nats_client_connect(self) -> None:
        """Scenario: to_connect_kwargs() output is accepted by nats-py Client.connect().

        This test verifies the kwargs structure is compatible with nats-py
        by inspecting the Client.connect() signature. It does NOT require
        a running NATS server.
        """
        import inspect

        try:
            from nats.aio.client import Client  # type: ignore[import-untyped]
        except ImportError:
            pytest.skip("nats-py not installed")

        cfg = NATSConfig()
        kwargs = cfg.to_connect_kwargs()

        sig = inspect.signature(Client.connect)
        params = sig.parameters

        for key in kwargs:
            assert key in params, (
                f"to_connect_kwargs() key '{key}' not accepted by Client.connect()"
            )
