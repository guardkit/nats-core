"""Tests for Jarvis event payload schemas.

Validates IntentClassifiedPayload, DispatchPayload, AgentResultPayload,
and NotificationPayload against acceptance criteria for TASK-ETS3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Factory helpers (conftest-style factory functions in-file for minimal mode)
# ---------------------------------------------------------------------------


@dataclass
class MockIntentClassifiedData:
    input_text: str = "build me a REST API"
    intent: str = "software.build"
    confidence: float = 0.95
    target_agent: str = "guardkit-factory"
    correlation_id: str | None = None


def make_intent_classified(**overrides: Any) -> dict[str, Any]:
    defaults = MockIntentClassifiedData()
    data: dict[str, Any] = {
        "input_text": defaults.input_text,
        "intent": defaults.intent,
        "confidence": defaults.confidence,
        "target_agent": defaults.target_agent,
        "correlation_id": defaults.correlation_id,
    }
    data.update(overrides)
    return data


@dataclass
class MockDispatchData:
    intent: str = "software.build"
    target_agent: str = "guardkit-factory"
    input_text: str = "build me a REST API"
    correlation_id: str = "corr-001"
    context: dict[str, Any] = field(default_factory=dict)


def make_dispatch(**overrides: Any) -> dict[str, Any]:
    defaults = MockDispatchData()
    data: dict[str, Any] = {
        "intent": defaults.intent,
        "target_agent": defaults.target_agent,
        "input_text": defaults.input_text,
        "correlation_id": defaults.correlation_id,
        "context": defaults.context,
    }
    data.update(overrides)
    return data


@dataclass
class MockAgentResultData:
    agent_id: str = "guardkit-factory"
    intent: str = "software.build"
    result: dict[str, Any] = field(default_factory=lambda: {"status": "ok"})
    correlation_id: str = "corr-001"
    success: bool = True


def make_agent_result(**overrides: Any) -> dict[str, Any]:
    defaults = MockAgentResultData()
    data: dict[str, Any] = {
        "agent_id": defaults.agent_id,
        "intent": defaults.intent,
        "result": defaults.result,
        "correlation_id": defaults.correlation_id,
        "success": defaults.success,
    }
    data.update(overrides)
    return data


@dataclass
class MockNotificationData:
    message: str = "Build completed successfully"
    level: str = "info"
    adapter: str = "slack"
    correlation_id: str | None = None


def make_notification(**overrides: Any) -> dict[str, Any]:
    defaults = MockNotificationData()
    data: dict[str, Any] = {
        "message": defaults.message,
        "level": defaults.level,
        "adapter": defaults.adapter,
        "correlation_id": defaults.correlation_id,
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# IntentClassifiedPayload tests
# ---------------------------------------------------------------------------


class TestIntentClassifiedPayload:
    """Tests for IntentClassifiedPayload model."""

    @pytest.mark.smoke
    def test_valid_construction(self) -> None:
        from nats_core.events._jarvis import IntentClassifiedPayload

        data = make_intent_classified()
        payload = IntentClassifiedPayload(**data)
        assert payload.input_text == "build me a REST API"
        assert payload.intent == "software.build"
        assert payload.confidence == 0.95
        assert payload.target_agent == "guardkit-factory"
        assert payload.correlation_id is None

    @pytest.mark.smoke
    def test_correlation_id_optional(self) -> None:
        from nats_core.events._jarvis import IntentClassifiedPayload

        data = make_intent_classified(correlation_id="corr-123")
        payload = IntentClassifiedPayload(**data)
        assert payload.correlation_id == "corr-123"

    @pytest.mark.boundary
    def test_confidence_lower_bound(self) -> None:
        from nats_core.events._jarvis import IntentClassifiedPayload

        data = make_intent_classified(confidence=0.0)
        payload = IntentClassifiedPayload(**data)
        assert payload.confidence == 0.0

    @pytest.mark.boundary
    def test_confidence_upper_bound(self) -> None:
        from nats_core.events._jarvis import IntentClassifiedPayload

        data = make_intent_classified(confidence=1.0)
        payload = IntentClassifiedPayload(**data)
        assert payload.confidence == 1.0

    @pytest.mark.negative
    def test_confidence_below_zero_rejected(self) -> None:
        from nats_core.events._jarvis import IntentClassifiedPayload

        data = make_intent_classified(confidence=-0.1)
        with pytest.raises(ValidationError):
            IntentClassifiedPayload(**data)

    @pytest.mark.negative
    def test_confidence_above_one_rejected(self) -> None:
        from nats_core.events._jarvis import IntentClassifiedPayload

        data = make_intent_classified(confidence=1.1)
        with pytest.raises(ValidationError):
            IntentClassifiedPayload(**data)

    @pytest.mark.negative
    def test_missing_required_fields(self) -> None:
        from nats_core.events._jarvis import IntentClassifiedPayload

        with pytest.raises(ValidationError):
            IntentClassifiedPayload()  # type: ignore[call-arg]

    @pytest.mark.edge_case
    def test_extra_fields_ignored(self) -> None:
        from nats_core.events._jarvis import IntentClassifiedPayload

        data = make_intent_classified(extra_field="should be ignored")
        payload = IntentClassifiedPayload(**data)
        assert not hasattr(payload, "extra_field")

    def test_field_descriptions_present(self) -> None:
        from nats_core.events._jarvis import IntentClassifiedPayload

        fields = IntentClassifiedPayload.model_fields
        for name, info in fields.items():
            assert info.description is not None, f"Field '{name}' missing description"
            assert len(info.description) > 0, f"Field '{name}' has empty description"


# ---------------------------------------------------------------------------
# DispatchPayload tests
# ---------------------------------------------------------------------------


class TestDispatchPayload:
    """Tests for DispatchPayload model."""

    @pytest.mark.smoke
    def test_valid_construction(self) -> None:
        from nats_core.events._jarvis import DispatchPayload

        data = make_dispatch()
        payload = DispatchPayload(**data)
        assert payload.intent == "software.build"
        assert payload.target_agent == "guardkit-factory"
        assert payload.input_text == "build me a REST API"
        assert payload.correlation_id == "corr-001"
        assert payload.context == {}

    @pytest.mark.key_example
    def test_context_with_data(self) -> None:
        from nats_core.events._jarvis import DispatchPayload

        ctx = {"repo": "finproxy", "branch": "main"}
        data = make_dispatch(context=ctx)
        payload = DispatchPayload(**data)
        assert payload.context == ctx

    @pytest.mark.negative
    def test_missing_correlation_id_rejected(self) -> None:
        from nats_core.events._jarvis import DispatchPayload

        data = make_dispatch()
        del data["correlation_id"]
        with pytest.raises(ValidationError):
            DispatchPayload(**data)

    @pytest.mark.edge_case
    def test_extra_fields_ignored(self) -> None:
        from nats_core.events._jarvis import DispatchPayload

        data = make_dispatch(unknown="value")
        payload = DispatchPayload(**data)
        assert not hasattr(payload, "unknown")

    def test_field_descriptions_present(self) -> None:
        from nats_core.events._jarvis import DispatchPayload

        fields = DispatchPayload.model_fields
        for name, info in fields.items():
            assert info.description is not None, f"Field '{name}' missing description"
            assert len(info.description) > 0, f"Field '{name}' has empty description"


# ---------------------------------------------------------------------------
# AgentResultPayload tests
# ---------------------------------------------------------------------------


class TestAgentResultPayload:
    """Tests for AgentResultPayload model."""

    @pytest.mark.smoke
    def test_valid_construction(self) -> None:
        from nats_core.events._jarvis import AgentResultPayload

        data = make_agent_result()
        payload = AgentResultPayload(**data)
        assert payload.agent_id == "guardkit-factory"
        assert payload.intent == "software.build"
        assert payload.result == {"status": "ok"}
        assert payload.correlation_id == "corr-001"
        assert payload.success is True

    @pytest.mark.key_example
    def test_failure_result(self) -> None:
        from nats_core.events._jarvis import AgentResultPayload

        data = make_agent_result(
            success=False,
            result={"error": "build failed", "code": 1},
        )
        payload = AgentResultPayload(**data)
        assert payload.success is False
        assert payload.result["error"] == "build failed"

    @pytest.mark.negative
    def test_missing_required_fields(self) -> None:
        from nats_core.events._jarvis import AgentResultPayload

        with pytest.raises(ValidationError):
            AgentResultPayload()  # type: ignore[call-arg]

    @pytest.mark.edge_case
    def test_extra_fields_ignored(self) -> None:
        from nats_core.events._jarvis import AgentResultPayload

        data = make_agent_result(extra="ignored")
        payload = AgentResultPayload(**data)
        assert not hasattr(payload, "extra")

    def test_field_descriptions_present(self) -> None:
        from nats_core.events._jarvis import AgentResultPayload

        fields = AgentResultPayload.model_fields
        for name, info in fields.items():
            assert info.description is not None, f"Field '{name}' missing description"
            assert len(info.description) > 0, f"Field '{name}' has empty description"


# ---------------------------------------------------------------------------
# NotificationPayload tests
# ---------------------------------------------------------------------------


class TestNotificationPayload:
    """Tests for NotificationPayload model."""

    @pytest.mark.smoke
    def test_valid_construction(self) -> None:
        from nats_core.events._jarvis import NotificationPayload

        data = make_notification()
        payload = NotificationPayload(**data)
        assert payload.message == "Build completed successfully"
        assert payload.level == "info"
        assert payload.adapter == "slack"
        assert payload.correlation_id is None

    @pytest.mark.key_example
    def test_warning_level(self) -> None:
        from nats_core.events._jarvis import NotificationPayload

        data = make_notification(level="warning")
        payload = NotificationPayload(**data)
        assert payload.level == "warning"

    @pytest.mark.key_example
    def test_error_level(self) -> None:
        from nats_core.events._jarvis import NotificationPayload

        data = make_notification(level="error")
        payload = NotificationPayload(**data)
        assert payload.level == "error"

    @pytest.mark.negative
    def test_invalid_level_rejected(self) -> None:
        from nats_core.events._jarvis import NotificationPayload

        data = make_notification(level="debug")
        with pytest.raises(ValidationError):
            NotificationPayload(**data)

    @pytest.mark.smoke
    def test_level_defaults_to_info(self) -> None:
        from nats_core.events._jarvis import NotificationPayload

        payload = NotificationPayload(message="test", adapter="email")
        assert payload.level == "info"

    @pytest.mark.smoke
    def test_correlation_id_optional(self) -> None:
        from nats_core.events._jarvis import NotificationPayload

        data = make_notification(correlation_id="corr-456")
        payload = NotificationPayload(**data)
        assert payload.correlation_id == "corr-456"

    @pytest.mark.edge_case
    def test_extra_fields_ignored(self) -> None:
        from nats_core.events._jarvis import NotificationPayload

        data = make_notification(extra="ignored")
        payload = NotificationPayload(**data)
        assert not hasattr(payload, "extra")

    def test_field_descriptions_present(self) -> None:
        from nats_core.events._jarvis import NotificationPayload

        fields = NotificationPayload.model_fields
        for name, info in fields.items():
            assert info.description is not None, f"Field '{name}' missing description"
            assert len(info.description) > 0, f"Field '{name}' has empty description"


# ---------------------------------------------------------------------------
# Re-export tests
# ---------------------------------------------------------------------------


class TestReExports:
    """Tests for public re-exports from events/__init__.py."""

    @pytest.mark.smoke
    def test_all_classes_exported_from_events(self) -> None:
        from nats_core.events import (
            AgentResultPayload,
            DispatchPayload,
            IntentClassifiedPayload,
            NotificationPayload,
        )

        assert IntentClassifiedPayload is not None
        assert DispatchPayload is not None
        assert AgentResultPayload is not None
        assert NotificationPayload is not None

    def test_all_in_events_dunder_all(self) -> None:
        import nats_core.events as events_mod

        expected = {
            "IntentClassifiedPayload",
            "DispatchPayload",
            "AgentResultPayload",
            "NotificationPayload",
        }
        assert expected.issubset(set(events_mod.__all__))
