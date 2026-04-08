"""Tests for nats_core.agent_config — AgentConfig, ModelConfig, GraphitiConfig.

Covers acceptance criteria AC-004 through AC-010 from TASK-NC01.
Uses factory functions from ``tests/conftest.py``.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from nats_core.agent_config import AgentConfig, GraphitiConfig, ModelConfig
from nats_core.config import NATSConfig


def _make(**overrides: Any) -> AgentConfig:
    """Thin wrapper: always provides a valid ``models`` unless overridden."""
    defaults: dict[str, Any] = {"models": ModelConfig(reasoning_model="gpt-4")}
    defaults.update(overrides)
    return AgentConfig(**defaults)


# ---------------------------------------------------------------------------
# AC-001 / AC-002 / AC-003 — NATSConfig (already tested in test_config.py,
# but we verify the existing config module still works)
# ---------------------------------------------------------------------------


@pytest.mark.smoke
class TestNATSConfigExisting:
    """Verify existing NATSConfig behaviour is preserved."""

    def test_defaults_without_env_vars(self) -> None:
        """AC-001: NATSConfig() instantiates with all defaults."""
        cfg = NATSConfig()
        assert cfg.url == "nats://localhost:4222"
        assert cfg.connect_timeout == 5.0
        assert cfg.reconnect_time_wait == 2.0
        assert cfg.max_reconnect_attempts == 60
        assert cfg.name == "nats-core-client"
        assert cfg.user is None
        assert cfg.password is None
        assert cfg.creds_file is None

    def test_url_override(self) -> None:
        """AC-002: NATSConfig(url=...) overrides correctly."""
        cfg = NATSConfig(url="nats://remote:4222")
        assert cfg.url == "nats://remote:4222"

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-003: NATSConfig reads from NATS_URL env var."""
        monkeypatch.setenv("NATS_URL", "nats://env-host:4222")
        cfg = NATSConfig()
        assert cfg.url == "nats://env-host:4222"

    def test_env_connect_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-003: NATSConfig reads NATS_CONNECT_TIMEOUT from env."""
        monkeypatch.setenv("NATS_CONNECT_TIMEOUT", "10.0")
        cfg = NATSConfig()
        assert cfg.connect_timeout == 10.0

    def test_env_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AC-003: NATSConfig reads NATS_NAME from env."""
        monkeypatch.setenv("NATS_NAME", "custom-client")
        cfg = NATSConfig()
        assert cfg.name == "custom-client"


# ---------------------------------------------------------------------------
# ModelConfig tests
# ---------------------------------------------------------------------------


class TestModelConfig:
    """Tests for ModelConfig nested model."""

    def test_reasoning_model_required(self) -> None:
        """ModelConfig requires reasoning_model to be provided."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig()  # type: ignore[call-arg]
        assert "reasoning_model" in str(exc_info.value)

    def test_reasoning_model_provided(self) -> None:
        """ModelConfig accepts reasoning_model."""
        mc = ModelConfig(reasoning_model="gpt-4")
        assert mc.reasoning_model == "gpt-4"
        assert mc.reasoning_endpoint == ""
        assert mc.implementation_model is None
        assert mc.implementation_endpoint is None
        assert mc.embedding_model is None
        assert mc.embedding_endpoint is None

    def test_all_fields_provided(self) -> None:
        """ModelConfig accepts all optional fields."""
        mc = ModelConfig(
            reasoning_model="gpt-4",
            reasoning_endpoint="https://api.openai.com/v1",
            implementation_model="gpt-3.5-turbo",
            implementation_endpoint="https://api.openai.com/v1",
            embedding_model="text-embedding-3-small",
            embedding_endpoint="https://api.openai.com/v1",
        )
        assert mc.reasoning_model == "gpt-4"
        assert mc.reasoning_endpoint == "https://api.openai.com/v1"
        assert mc.implementation_model == "gpt-3.5-turbo"
        assert mc.implementation_endpoint == "https://api.openai.com/v1"
        assert mc.embedding_model == "text-embedding-3-small"
        assert mc.embedding_endpoint == "https://api.openai.com/v1"

    def test_reasoning_model_blank_rejected(self) -> None:
        """ModelConfig rejects blank reasoning_model."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(reasoning_model="")
        assert "reasoning_model" in str(exc_info.value)


# ---------------------------------------------------------------------------
# GraphitiConfig tests
# ---------------------------------------------------------------------------


class TestGraphitiConfig:
    """Tests for GraphitiConfig nested model."""

    def test_defaults(self) -> None:
        """GraphitiConfig has sensible defaults."""
        gc = GraphitiConfig()
        assert gc.endpoint == "bolt://localhost:7687"
        assert gc.default_group_ids == ["appmilla-fleet"]

    def test_override_endpoint(self) -> None:
        """GraphitiConfig endpoint can be overridden."""
        gc = GraphitiConfig(endpoint="bolt://remote:7687")
        assert gc.endpoint == "bolt://remote:7687"

    def test_override_group_ids(self) -> None:
        """GraphitiConfig default_group_ids can be overridden."""
        gc = GraphitiConfig(default_group_ids=["custom-group", "another"])
        assert gc.default_group_ids == ["custom-group", "another"]

    def test_default_group_ids_independent(self) -> None:
        """GraphitiConfig instances have independent default_group_ids."""
        gc1 = GraphitiConfig()
        gc2 = GraphitiConfig()
        gc1.default_group_ids.append("extra")
        assert "extra" not in gc2.default_group_ids


# ---------------------------------------------------------------------------
# AC-004 — AgentConfig requires models
# ---------------------------------------------------------------------------


class TestAgentConfigModelsRequired:
    """AC-004: AgentConfig requires models to be provided."""

    def test_missing_models_rejected(self) -> None:
        """AgentConfig without models raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig()  # type: ignore[call-arg]
        assert "models" in str(exc_info.value)

    def test_models_provided(self) -> None:
        """AgentConfig with models succeeds."""
        cfg = _make()
        assert cfg.models.reasoning_model == "gpt-4"


# ---------------------------------------------------------------------------
# AC-005 — AgentConfig.nats is a valid NATSConfig
# ---------------------------------------------------------------------------


class TestAgentConfigNats:
    """AC-005: AgentConfig.nats is a valid NATSConfig."""

    def test_default_nats(self) -> None:
        """AgentConfig.nats defaults to a NATSConfig with standard defaults."""
        cfg = _make()
        assert isinstance(cfg.nats, NATSConfig)
        assert cfg.nats.url == "nats://localhost:4222"
        assert cfg.nats.connect_timeout == 5.0

    def test_nats_override_with_instance(self) -> None:
        """AgentConfig.nats can be overridden with a NATSConfig instance."""
        custom_nats = NATSConfig(url="nats://custom:4222")
        cfg = _make(nats=custom_nats)
        assert cfg.nats.url == "nats://custom:4222"

    def test_nats_override_with_dict(self) -> None:
        """AgentConfig.nats can be provided as a dict."""
        cfg = _make(nats={"url": "nats://dict-host:4222"})
        assert isinstance(cfg.nats, NATSConfig)
        assert cfg.nats.url == "nats://dict-host:4222"

    def test_nats_standalone_import(self) -> None:
        """NATSConfig can be used standalone (not nested)."""
        nats = NATSConfig(url="nats://standalone:4222")
        assert nats.url == "nats://standalone:4222"


# ---------------------------------------------------------------------------
# AC-006 — Heartbeat invariant
# ---------------------------------------------------------------------------


class TestHeartbeatInvariant:
    """AC-006: heartbeat_timeout_seconds > heartbeat_interval_seconds invariant."""

    def test_default_heartbeat_valid(self) -> None:
        """Default heartbeat values satisfy the invariant (90 > 30)."""
        cfg = _make()
        assert cfg.heartbeat_timeout_seconds > cfg.heartbeat_interval_seconds
        assert cfg.heartbeat_interval_seconds == 30
        assert cfg.heartbeat_timeout_seconds == 90

    def test_timeout_greater_than_interval_accepted(self) -> None:
        """Custom values satisfying invariant are accepted."""
        cfg = _make(heartbeat_interval_seconds=10, heartbeat_timeout_seconds=31)
        assert cfg.heartbeat_timeout_seconds > cfg.heartbeat_interval_seconds

    def test_timeout_equal_to_interval_rejected(self) -> None:
        """Equal timeout and interval is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            _make(heartbeat_interval_seconds=30, heartbeat_timeout_seconds=30)
        errors = str(exc_info.value)
        assert "heartbeat_timeout_seconds" in errors

    def test_timeout_less_than_interval_rejected(self) -> None:
        """Timeout less than interval is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            _make(heartbeat_interval_seconds=60, heartbeat_timeout_seconds=30)
        errors = str(exc_info.value)
        assert "heartbeat_timeout_seconds" in errors

    def test_minimal_valid_heartbeat(self) -> None:
        """Minimum valid: interval=1, timeout=2."""
        cfg = _make(heartbeat_interval_seconds=1, heartbeat_timeout_seconds=2)
        assert cfg.heartbeat_interval_seconds == 1
        assert cfg.heartbeat_timeout_seconds == 2


# ---------------------------------------------------------------------------
# AgentConfig defaults and field tests
# ---------------------------------------------------------------------------


class TestAgentConfigDefaults:
    """Test AgentConfig default field values."""

    def test_graphiti_default_none(self) -> None:
        """GraphitiConfig is None by default."""
        cfg = _make()
        assert cfg.graphiti is None

    def test_graphiti_provided(self) -> None:
        """GraphitiConfig can be provided."""
        cfg = _make(graphiti=GraphitiConfig())
        assert cfg.graphiti is not None
        assert cfg.graphiti.endpoint == "bolt://localhost:7687"

    def test_langsmith_defaults_none(self) -> None:
        """LangSmith fields default to None."""
        cfg = _make()
        assert cfg.langsmith_project is None
        assert cfg.langsmith_api_key is None

    def test_max_task_timeout_default(self) -> None:
        """max_task_timeout_seconds defaults to 600."""
        cfg = _make()
        assert cfg.max_task_timeout_seconds == 600

    def test_api_keys_default_none(self) -> None:
        """All API key fields default to None."""
        cfg = _make()
        assert cfg.gemini_api_key is None
        assert cfg.anthropic_api_key is None
        assert cfg.openai_api_key is None

    def test_api_keys_masked(self) -> None:
        """API keys are masked in repr (SecretStr)."""
        cfg = _make(
            gemini_api_key="gemini-secret",
            anthropic_api_key="anthropic-secret",
            openai_api_key="openai-secret",
            langsmith_api_key="langsmith-secret",
        )
        text = repr(cfg)
        assert "gemini-secret" not in text
        assert "anthropic-secret" not in text
        assert "openai-secret" not in text
        assert "langsmith-secret" not in text

    def test_api_keys_accessible_via_get_secret_value(self) -> None:
        """API keys can be read via get_secret_value()."""
        cfg = _make(
            openai_api_key="sk-test-key",
        )
        assert cfg.openai_api_key is not None
        assert cfg.openai_api_key.get_secret_value() == "sk-test-key"


# ---------------------------------------------------------------------------
# AgentConfig env var override tests
# ---------------------------------------------------------------------------


class TestAgentConfigEnvOverride:
    """Test AgentConfig reads from environment variables."""

    def test_env_models_reasoning_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AgentConfig reads AGENT_MODELS__REASONING_MODEL from env."""
        monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "claude-3-opus")
        cfg = AgentConfig()  # type: ignore[call-arg]
        assert cfg.models.reasoning_model == "claude-3-opus"

    def test_env_heartbeat_interval(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AgentConfig reads AGENT_HEARTBEAT_INTERVAL_SECONDS from env."""
        monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "gpt-4")
        monkeypatch.setenv("AGENT_HEARTBEAT_INTERVAL_SECONDS", "15")
        cfg = AgentConfig()  # type: ignore[call-arg]
        assert cfg.heartbeat_interval_seconds == 15

    def test_env_heartbeat_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AgentConfig reads AGENT_HEARTBEAT_TIMEOUT_SECONDS from env."""
        monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "gpt-4")
        monkeypatch.setenv("AGENT_HEARTBEAT_TIMEOUT_SECONDS", "120")
        cfg = AgentConfig()  # type: ignore[call-arg]
        assert cfg.heartbeat_timeout_seconds == 120

    def test_env_langsmith_project(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AgentConfig reads AGENT_LANGSMITH_PROJECT from env."""
        monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "gpt-4")
        monkeypatch.setenv("AGENT_LANGSMITH_PROJECT", "my-project")
        cfg = AgentConfig()  # type: ignore[call-arg]
        assert cfg.langsmith_project == "my-project"

    def test_env_max_task_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AgentConfig reads AGENT_MAX_TASK_TIMEOUT_SECONDS from env."""
        monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "gpt-4")
        monkeypatch.setenv("AGENT_MAX_TASK_TIMEOUT_SECONDS", "1200")
        cfg = AgentConfig()  # type: ignore[call-arg]
        assert cfg.max_task_timeout_seconds == 1200

    def test_env_graphiti_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AgentConfig reads AGENT_GRAPHITI__ENDPOINT from env."""
        monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "gpt-4")
        monkeypatch.setenv("AGENT_GRAPHITI__ENDPOINT", "bolt://remote:7687")
        cfg = AgentConfig()  # type: ignore[call-arg]
        assert cfg.graphiti is not None
        assert cfg.graphiti.endpoint == "bolt://remote:7687"


# ---------------------------------------------------------------------------
# Boundary tests
# ---------------------------------------------------------------------------


class TestAgentConfigBoundary:
    """Boundary value tests for AgentConfig fields."""

    def test_heartbeat_interval_zero_rejected(self) -> None:
        """heartbeat_interval_seconds = 0 is rejected (ge=1)."""
        with pytest.raises(ValidationError) as exc_info:
            _make(heartbeat_interval_seconds=0)
        assert "heartbeat_interval_seconds" in str(exc_info.value)

    def test_heartbeat_timeout_zero_rejected(self) -> None:
        """heartbeat_timeout_seconds = 0 is rejected (ge=1)."""
        with pytest.raises(ValidationError) as exc_info:
            _make(heartbeat_timeout_seconds=0)
        assert "heartbeat_timeout_seconds" in str(exc_info.value)

    def test_max_task_timeout_zero_rejected(self) -> None:
        """max_task_timeout_seconds = 0 is rejected (ge=1)."""
        with pytest.raises(ValidationError) as exc_info:
            _make(max_task_timeout_seconds=0)
        assert "max_task_timeout_seconds" in str(exc_info.value)

    def test_heartbeat_interval_negative_rejected(self) -> None:
        """Negative heartbeat_interval_seconds is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            _make(heartbeat_interval_seconds=-1)
        assert "heartbeat_interval_seconds" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-007 — from __future__ import annotations
# ---------------------------------------------------------------------------


class TestFutureAnnotations:
    """AC-007: Both modules have from __future__ import annotations."""

    def test_config_module_has_future_annotations(self) -> None:
        """config.py has from __future__ import annotations."""
        import nats_core.config as config_mod

        assert hasattr(config_mod, "annotations") or "annotations" in dir(config_mod)
        # Verify by inspecting source
        import inspect

        source = inspect.getsource(config_mod)
        assert "from __future__ import annotations" in source

    def test_agent_config_module_has_future_annotations(self) -> None:
        """agent_config.py has from __future__ import annotations."""
        import inspect

        import nats_core.agent_config as agent_config_mod

        source = inspect.getsource(agent_config_mod)
        assert "from __future__ import annotations" in source


# ---------------------------------------------------------------------------
# AC-008 — All fields have Field(description=...)
# ---------------------------------------------------------------------------


class TestFieldDescriptions:
    """AC-008: All fields have Field(description=...)."""

    def test_nats_config_fields_have_descriptions(self) -> None:
        """Every NATSConfig field has a description."""
        for name, info in NATSConfig.model_fields.items():
            assert info.description is not None and info.description.strip(), (
                f"NATSConfig.{name} is missing Field(description=...)"
            )

    def test_model_config_fields_have_descriptions(self) -> None:
        """Every ModelConfig field has a description."""
        for name, info in ModelConfig.model_fields.items():
            assert info.description is not None and info.description.strip(), (
                f"ModelConfig.{name} is missing Field(description=...)"
            )

    def test_graphiti_config_fields_have_descriptions(self) -> None:
        """Every GraphitiConfig field has a description."""
        for name, info in GraphitiConfig.model_fields.items():
            assert info.description is not None and info.description.strip(), (
                f"GraphitiConfig.{name} is missing Field(description=...)"
            )

    def test_agent_config_fields_have_descriptions(self) -> None:
        """Every AgentConfig field has a description."""
        for name, info in AgentConfig.model_fields.items():
            assert info.description is not None and info.description.strip(), (
                f"AgentConfig.{name} is missing Field(description=...)"
            )


# ---------------------------------------------------------------------------
# AC-009 — py.typed exists
# ---------------------------------------------------------------------------


class TestPyTyped:
    """AC-009: py.typed exists in src/nats_core/."""

    def test_py_typed_marker_exists(self) -> None:
        """py.typed marker file exists in the package directory."""
        import importlib.resources

        # Use importlib.resources for robust path resolution
        ref = importlib.resources.files("nats_core").joinpath("py.typed")
        assert ref.is_file(), "py.typed marker missing from src/nats_core/"


# ---------------------------------------------------------------------------
# Public API export tests
# ---------------------------------------------------------------------------


class TestPublicApiExports:
    """Verify AgentConfig, ModelConfig, GraphitiConfig are exported from nats_core."""

    def test_agent_config_importable_from_package(self) -> None:
        """AgentConfig is importable from nats_core."""
        from nats_core import AgentConfig as AC

        assert AC is AgentConfig

    def test_model_config_importable_from_package(self) -> None:
        """ModelConfig is importable from nats_core."""
        from nats_core import ModelConfig as MC

        assert MC is ModelConfig

    def test_graphiti_config_importable_from_package(self) -> None:
        """GraphitiConfig is importable from nats_core."""
        from nats_core import GraphitiConfig as GC

        assert GC is GraphitiConfig
