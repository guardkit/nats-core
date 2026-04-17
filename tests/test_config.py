"""Tests for nats_core.config — NATSConfig pydantic-settings model.

Covers all 23 BDD scenarios from
``features/nats-configuration/nats-configuration.feature``.
Uses ``_make()`` factory from ``tests/conftest.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from nats_core.config import NATSConfig

pytestmark = pytest.mark.unit


def _make(**overrides: Any) -> NATSConfig:
    """Thin wrapper delegating to the conftest factory for readability."""
    return NATSConfig(**overrides)

# ---------------------------------------------------------------------------
# Smoke tests (BDD @smoke)
# ---------------------------------------------------------------------------


@pytest.mark.smoke
def test_default_url() -> None:
    """Scenario: Default configuration connects to localhost."""
    cfg = _make()
    assert cfg.url == "nats://localhost:4222"
    assert cfg.connect_timeout == 5.0
    assert cfg.reconnect_time_wait == 2.0
    assert cfg.max_reconnect_attempts == 60
    assert cfg.name == "nats-core-client"


@pytest.mark.smoke
def test_env_url_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: Environment variable overrides the default URL."""
    monkeypatch.setenv("NATS_URL", "nats://gb10.tail:4222")
    cfg = _make()
    assert cfg.url == "nats://gb10.tail:4222"


# ---------------------------------------------------------------------------
# Key-example tests (BDD @key-example)
# ---------------------------------------------------------------------------


def test_env_user_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: Configuring user and password authentication from environment."""
    monkeypatch.setenv("NATS_USER", "appmilla")
    monkeypatch.setenv("NATS_PASSWORD", "s3cret")
    cfg = _make()
    assert cfg.user == "appmilla"
    assert cfg.password is not None
    assert cfg.password.get_secret_value() == "s3cret"


def test_env_creds_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: Configuring NKey credentials file from environment."""
    monkeypatch.setenv("NATS_CREDS_FILE", "/etc/nats/appmilla.creds")
    cfg = _make()
    assert cfg.creds_file == "/etc/nats/appmilla.creds"


def test_constructor_override() -> None:
    """Scenario: Constructor arguments override defaults."""
    cfg = _make(
        url="nats://test:4222",
        connect_timeout=1.0,
    )
    assert cfg.url == "nats://test:4222"
    assert cfg.connect_timeout == 1.0
    # Other fields retain defaults
    assert cfg.reconnect_time_wait == 2.0
    assert cfg.max_reconnect_attempts == 60
    assert cfg.name == "nats-core-client"


# ---------------------------------------------------------------------------
# Boundary tests (BDD @boundary)
# ---------------------------------------------------------------------------


def test_connect_timeout_zero() -> None:
    """Scenario: Connect timeout at zero is accepted."""
    cfg = _make(connect_timeout=0.0)
    assert cfg.connect_timeout == 0.0


def test_connect_timeout_negative() -> None:
    """Scenario: Negative connect timeout is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _make(connect_timeout=-1.0)
    assert "connect_timeout" in str(exc_info.value)


def test_reconnect_time_wait_zero() -> None:
    """Scenario: Reconnect time wait at zero is accepted."""
    cfg = _make(reconnect_time_wait=0.0)
    assert cfg.reconnect_time_wait == 0.0


def test_reconnect_time_wait_negative() -> None:
    """Scenario: Negative reconnect time wait is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _make(reconnect_time_wait=-1.0)
    assert "reconnect_time_wait" in str(exc_info.value)


def test_max_reconnect_attempts_zero() -> None:
    """Scenario: Max reconnect attempts at zero means no retries."""
    cfg = _make(max_reconnect_attempts=0)
    assert cfg.max_reconnect_attempts == 0


def test_max_reconnect_attempts_negative() -> None:
    """Scenario: Negative max reconnect attempts is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _make(max_reconnect_attempts=-1)
    assert "max_reconnect_attempts" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Negative tests (BDD @negative)
# ---------------------------------------------------------------------------


def test_invalid_url_scheme() -> None:
    """Scenario: Invalid URL scheme is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _make(url="http://localhost:4222")
    assert "url" in str(exc_info.value).lower()


def test_empty_url() -> None:
    """Scenario: Empty URL is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _make(url="")
    assert "url" in str(exc_info.value).lower()


def test_empty_name() -> None:
    """Scenario: Empty client name is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _make(name="")
    assert "name" in str(exc_info.value).lower()


def test_user_without_password(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: User without password is rejected."""
    monkeypatch.setenv("NATS_USER", "appmilla")
    monkeypatch.delenv("NATS_PASSWORD", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        _make()
    errors = str(exc_info.value)
    assert "user" in errors.lower() or "password" in errors.lower()


# ---------------------------------------------------------------------------
# Edge-case tests (BDD @edge-case)
# ---------------------------------------------------------------------------


def test_env_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: Environment variable precedence over defaults."""
    monkeypatch.setenv("NATS_URL", "nats://env-server:4222")
    cfg = _make()
    assert cfg.url == "nats://env-server:4222"


def test_instances_independent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario: Multiple NATSConfig instances are independent."""
    monkeypatch.setenv("NATS_URL", "nats://shared:4222")
    cfg1 = _make()
    cfg2 = _make()
    # Mutate the first instance
    object.__setattr__(cfg1, "url", "nats://modified:4222")
    # Second instance must be unaffected
    assert cfg2.url == "nats://shared:4222"
    assert cfg1.url != cfg2.url


def test_dotenv_loading(tmp_path: Path) -> None:
    """Scenario: Configuration loads from dotenv file."""
    env_file = tmp_path / ".env"
    env_file.write_text('NATS_URL="nats://dotenv-server:4222"\n')
    cfg = NATSConfig(_env_file=env_file)  # type: ignore[call-arg]
    assert cfg.url == "nats://dotenv-server:4222"


def test_dotenv_with_sibling_keys_is_tolerated(tmp_path: Path) -> None:
    """Sibling (non-NATS_) keys in a shared .env file must not cause extra_forbidden."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        'NATS_URL="nats://shared-env:4222"\n'
        'OPENAI_API_KEY="sk-openai"\n'
        'GOOGLE_API_KEY="sk-google"\n'
        'TAVILY_API_KEY="sk-tavily"\n'
        'FALKORDB_HOST="whitestocks"\n'
    )
    cfg = NATSConfig(_env_file=env_file)  # type: ignore[call-arg]
    assert cfg.url == "nats://shared-env:4222"
    dumped = cfg.model_dump()
    for sibling in ("openai_api_key", "google_api_key", "tavily_api_key", "falkordb_host"):
        assert sibling not in dumped


def test_password_masked_repr() -> None:
    """Scenario: Sensitive fields are masked in string representation."""
    cfg = _make(user="admin", password="s3cret")
    text = repr(cfg)
    assert "s3cret" not in text
    assert "admin" in text


def test_password_masked_model_dump() -> None:
    """Scenario: Password is not exposed when config is serialised to dict."""
    cfg = _make(user="admin", password="s3cret")
    dumped = cfg.model_dump()
    assert "s3cret" not in str(dumped)


def test_creds_file_path_traversal() -> None:
    """Scenario: Creds file with path traversal is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _make(creds_file="../../etc/passwd")
    errors = str(exc_info.value)
    assert "creds_file" in errors.lower() or ".." in errors


@pytest.mark.integration
def test_to_connect_kwargs() -> None:
    """Scenario: Config produces valid nats-py connection kwargs."""
    cfg = _make(url="nats://gb10.tail:4222", connect_timeout=10.0)
    kwargs: dict[str, Any] = cfg.to_connect_kwargs()

    # Verify structure matches nats-py expectations
    assert kwargs["servers"] == ["nats://gb10.tail:4222"]
    assert kwargs["connect_timeout"] == 10.0
    assert kwargs["reconnect_time_wait"] == 2.0
    assert kwargs["max_reconnect_attempts"] == 60
    assert kwargs["name"] == "nats-core-client"

    # Verify the kwargs are accepted by nats-py Client.connect() signature
    import inspect

    try:
        from nats.aio.client import Client  # type: ignore[import-untyped,unused-ignore]
    except ImportError:
        pytest.skip("nats-py not installed")

    sig = inspect.signature(Client.connect)
    params = sig.parameters
    for key in kwargs:
        assert key in params, (
            f"to_connect_kwargs() key '{key}' not accepted by Client.connect()"
        )


def test_password_and_creds_mutually_exclusive() -> None:
    """Scenario: Providing both password auth and creds file is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        _make(user="admin", password="s3cret", creds_file="/etc/nats/appmilla.creds")
    errors = str(exc_info.value)
    assert "password" in errors.lower() or "creds_file" in errors.lower()
