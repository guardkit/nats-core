"""Tests for EventType enum and MessageEnvelope model (TASK-ME02)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError


class TestEventType:
    """Verify EventType enum has all 16 values across 4 domains."""

    def test_event_type_is_str_enum(self) -> None:
        """AC-001: EventType must be a str, Enum subclass."""
        from nats_core.envelope import EventType

        assert issubclass(EventType, str)
        from enum import Enum

        assert issubclass(EventType, Enum)

    def test_pipeline_domain_values(self) -> None:
        """AC-001: Pipeline domain has 6 event types."""
        from nats_core.envelope import EventType

        assert EventType.FEATURE_PLANNED == "feature_planned"
        assert EventType.FEATURE_READY_FOR_BUILD == "feature_ready_for_build"
        assert EventType.BUILD_STARTED == "build_started"
        assert EventType.BUILD_PROGRESS == "build_progress"
        assert EventType.BUILD_COMPLETE == "build_complete"
        assert EventType.BUILD_FAILED == "build_failed"

    def test_agent_domain_values(self) -> None:
        """AC-001: Agent domain has 6 event types."""
        from nats_core.envelope import EventType

        assert EventType.STATUS == "status"
        assert EventType.APPROVAL_REQUEST == "approval_request"
        assert EventType.APPROVAL_RESPONSE == "approval_response"
        assert EventType.COMMAND == "command"
        assert EventType.RESULT == "result"
        assert EventType.ERROR == "error"

    def test_jarvis_domain_values(self) -> None:
        """AC-001: Jarvis domain has 4 event types."""
        from nats_core.envelope import EventType

        assert EventType.INTENT_CLASSIFIED == "intent_classified"
        assert EventType.DISPATCH == "dispatch"
        assert EventType.AGENT_RESULT == "agent_result"
        assert EventType.NOTIFICATION == "notification"

    def test_fleet_domain_values(self) -> None:
        """AC-001: Fleet domain has 3 event types."""
        from nats_core.envelope import EventType

        assert EventType.AGENT_REGISTER == "agent_register"
        assert EventType.AGENT_HEARTBEAT == "agent_heartbeat"
        assert EventType.AGENT_DEREGISTER == "agent_deregister"

    def test_total_event_type_count(self) -> None:
        """AC-001: Exactly 19 event types total (6+6+4+3)."""
        from nats_core.envelope import EventType

        assert len(EventType) == 19

    def test_event_type_usable_as_string(self) -> None:
        """EventType values can be used as strings."""
        from nats_core.envelope import EventType

        val: str = EventType.BUILD_STARTED
        assert val == "build_started"
        assert isinstance(val, str)


class TestMessageEnvelope:
    """Verify MessageEnvelope model fields, defaults, and validation."""

    def _make_envelope(self, **overrides: Any) -> Any:
        """Helper to create a MessageEnvelope with defaults."""
        from nats_core.envelope import EventType, MessageEnvelope

        defaults: dict[str, Any] = {
            "source_id": "test-agent",
            "event_type": EventType.BUILD_STARTED,
            "payload": {"key": "value"},
        }
        defaults.update(overrides)
        return MessageEnvelope(**defaults)

    def test_required_fields_present(self) -> None:
        """AC-002: MessageEnvelope accepts required fields."""
        env = self._make_envelope()
        assert env.source_id == "test-agent"
        assert env.payload == {"key": "value"}

    def test_message_id_auto_generated_uuid(self) -> None:
        """AC-002: message_id defaults to a valid UUID string."""
        env = self._make_envelope()
        # Should be parseable as UUID
        parsed = UUID(env.message_id)
        assert str(parsed) == env.message_id

    def test_message_id_unique_per_instance(self) -> None:
        """AC-002: Each envelope gets a unique message_id."""
        env1 = self._make_envelope()
        env2 = self._make_envelope()
        assert env1.message_id != env2.message_id

    def test_timestamp_defaults_to_utc_now(self) -> None:
        """AC-002: timestamp defaults to approximately UTC now."""
        before = datetime.now(timezone.utc)
        env = self._make_envelope()
        after = datetime.now(timezone.utc)

        assert before <= env.timestamp <= after
        assert env.timestamp.tzinfo is not None

    def test_version_defaults_to_1_0(self) -> None:
        """AC-002: version defaults to '1.0'."""
        env = self._make_envelope()
        assert env.version == "1.0"

    def test_project_defaults_to_none(self) -> None:
        """AC-002: project defaults to None."""
        env = self._make_envelope()
        assert env.project is None

    def test_correlation_id_defaults_to_none(self) -> None:
        """AC-002: correlation_id defaults to None."""
        env = self._make_envelope()
        assert env.correlation_id is None

    def test_optional_fields_can_be_set(self) -> None:
        """AC-002: Optional fields accept values."""
        env = self._make_envelope(
            project="my-project",
            correlation_id="corr-123",
        )
        assert env.project == "my-project"
        assert env.correlation_id == "corr-123"

    def test_event_type_is_event_type_enum(self) -> None:
        """AC-002: event_type field is an EventType instance."""
        from nats_core.envelope import EventType

        env = self._make_envelope()
        assert isinstance(env.event_type, EventType)
        assert env.event_type == EventType.BUILD_STARTED

    def test_source_id_min_length_validation(self) -> None:
        """AC-002: source_id requires min_length=1."""
        with pytest.raises(ValidationError):
            self._make_envelope(source_id="")

    def test_missing_required_field_source_id(self) -> None:
        """AC-002: source_id is required."""
        from nats_core.envelope import EventType, MessageEnvelope

        with pytest.raises(ValidationError):
            MessageEnvelope(
                event_type=EventType.BUILD_STARTED,
                payload={"key": "value"},
            )  # type: ignore[call-arg]

    def test_missing_required_field_event_type(self) -> None:
        """AC-002: event_type is required."""
        from nats_core.envelope import MessageEnvelope

        with pytest.raises(ValidationError):
            MessageEnvelope(
                source_id="test-agent",
                payload={"key": "value"},
            )  # type: ignore[call-arg]

    def test_missing_required_field_payload(self) -> None:
        """AC-002: payload is required."""
        from nats_core.envelope import EventType, MessageEnvelope

        with pytest.raises(ValidationError):
            MessageEnvelope(
                source_id="test-agent",
                event_type=EventType.BUILD_STARTED,
            )  # type: ignore[call-arg]


class TestMessageEnvelopeConfig:
    """Verify model config and serialization behavior."""

    def _make_envelope(self, **overrides: Any) -> Any:
        """Helper to create a MessageEnvelope with defaults."""
        from nats_core.envelope import EventType, MessageEnvelope

        defaults: dict[str, Any] = {
            "source_id": "test-agent",
            "event_type": EventType.BUILD_STARTED,
            "payload": {"key": "value"},
        }
        defaults.update(overrides)
        return MessageEnvelope(**defaults)

    def test_extra_fields_ignored(self) -> None:
        """AC-003: model_config extra='ignore' for forward compatibility."""
        from nats_core.envelope import EventType, MessageEnvelope

        env = MessageEnvelope(
            source_id="test-agent",
            event_type=EventType.BUILD_STARTED,
            payload={"key": "value"},
            unknown_future_field="should be ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(env, "unknown_future_field")

    def test_json_serialisation_iso8601_timestamp(self) -> None:
        """AC-005: JSON serialisation uses ISO 8601 for timestamps."""
        env = self._make_envelope()
        json_str = env.model_dump_json()
        data = json.loads(json_str)
        ts = data["timestamp"]
        # ISO 8601 format check — must parse back
        parsed = datetime.fromisoformat(ts)
        assert parsed is not None

    def test_json_roundtrip(self) -> None:
        """MessageEnvelope can serialize to JSON and deserialize back."""
        from nats_core.envelope import MessageEnvelope

        env = self._make_envelope()
        json_str = env.model_dump_json()
        restored = MessageEnvelope.model_validate_json(json_str)
        assert restored.message_id == env.message_id
        assert restored.source_id == env.source_id
        assert restored.event_type == env.event_type
        assert restored.payload == env.payload

    def test_all_fields_have_descriptions(self) -> None:
        """AC-004: All fields must have Field(description=...)."""
        from nats_core.envelope import MessageEnvelope

        for name, field_info in MessageEnvelope.model_fields.items():
            assert field_info.description is not None, (
                f"Field '{name}' is missing description"
            )
            assert len(field_info.description) > 0, (
                f"Field '{name}' has empty description"
            )


class TestPayloadClassForEventType:
    """Verify payload_class_for_event_type helper function."""

    def test_raises_not_implemented_error(self) -> None:
        """AC-006: payload_class_for_event_type raises NotImplementedError."""
        from nats_core.envelope import EventType, payload_class_for_event_type

        with pytest.raises(NotImplementedError):
            payload_class_for_event_type(EventType.BUILD_STARTED)


class TestPublicApiReExport:
    """Verify public API is re-exported from nats_core."""

    def test_event_type_importable_from_root(self) -> None:
        """AC-007: EventType re-exported from nats_core."""
        from nats_core import EventType  # type: ignore[attr-defined]

        assert EventType is not None

    def test_message_envelope_importable_from_root(self) -> None:
        """AC-007: MessageEnvelope re-exported from nats_core."""
        from nats_core import MessageEnvelope  # type: ignore[attr-defined]

        assert MessageEnvelope is not None

    def test_payload_class_for_event_type_importable_from_root(self) -> None:
        """AC-007: payload_class_for_event_type re-exported from nats_core."""
        from nats_core import payload_class_for_event_type  # type: ignore[attr-defined]

        assert payload_class_for_event_type is not None


class TestFutureAnnotationsEnvelope:
    """Verify envelope module uses from __future__ import annotations."""

    def test_envelope_has_future_annotations(self) -> None:
        """AC-008: from __future__ import annotations at top of envelope.py."""
        from pathlib import Path

        envelope_path = (
            Path(__file__).resolve().parent.parent / "src" / "nats_core" / "envelope.py"
        )
        content = envelope_path.read_text()
        assert "from __future__ import annotations" in content
