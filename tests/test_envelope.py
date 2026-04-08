"""Tests for EventType enum and MessageEnvelope model (TASK-ME02 + TASK-ME03).

TASK-ME02: Unit tests for EventType and MessageEnvelope model fields/config.
TASK-ME03: All 23 BDD scenarios from features/message-envelope/message-envelope.feature.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from nats_core.envelope import EventType, MessageEnvelope
from tests.conftest import make_envelope, make_envelope_json

# ===========================================================================
# TASK-ME02 tests (pre-existing)
# ===========================================================================


class TestEventType:
    """Verify EventType enum has all 16 values across 4 domains."""

    def test_event_type_is_str_enum(self) -> None:
        """AC-001: EventType must be a str, Enum subclass."""
        assert issubclass(EventType, str)
        from enum import Enum

        assert issubclass(EventType, Enum)

    def test_pipeline_domain_values(self) -> None:
        """AC-001: Pipeline domain has 6 event types."""
        assert EventType.FEATURE_PLANNED == "feature_planned"
        assert EventType.FEATURE_READY_FOR_BUILD == "feature_ready_for_build"
        assert EventType.BUILD_STARTED == "build_started"
        assert EventType.BUILD_PROGRESS == "build_progress"
        assert EventType.BUILD_COMPLETE == "build_complete"
        assert EventType.BUILD_FAILED == "build_failed"

    def test_agent_domain_values(self) -> None:
        """AC-001: Agent domain has 6 event types."""
        assert EventType.STATUS == "status"
        assert EventType.APPROVAL_REQUEST == "approval_request"
        assert EventType.APPROVAL_RESPONSE == "approval_response"
        assert EventType.COMMAND == "command"
        assert EventType.RESULT == "result"
        assert EventType.ERROR == "error"

    def test_jarvis_domain_values(self) -> None:
        """AC-001: Jarvis domain has 4 event types."""
        assert EventType.INTENT_CLASSIFIED == "intent_classified"
        assert EventType.DISPATCH == "dispatch"
        assert EventType.AGENT_RESULT == "agent_result"
        assert EventType.NOTIFICATION == "notification"

    def test_fleet_domain_values(self) -> None:
        """AC-001: Fleet domain has 3 event types."""
        assert EventType.AGENT_REGISTER == "agent_register"
        assert EventType.AGENT_HEARTBEAT == "agent_heartbeat"
        assert EventType.AGENT_DEREGISTER == "agent_deregister"

    def test_total_event_type_count(self) -> None:
        """AC-001: Exactly 19 event types total (6+6+4+3)."""
        assert len(EventType) == 19

    def test_event_type_usable_as_string(self) -> None:
        """EventType values can be used as strings."""
        val: str = EventType.BUILD_STARTED
        assert val == "build_started"
        assert isinstance(val, str)


class TestMessageEnvelope:
    """Verify MessageEnvelope model fields, defaults, and validation."""

    def _make_envelope(self, **overrides: Any) -> MessageEnvelope:
        """Helper to create a MessageEnvelope with defaults."""
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
        env = self._make_envelope()
        assert isinstance(env.event_type, EventType)
        assert env.event_type == EventType.BUILD_STARTED

    def test_source_id_min_length_validation(self) -> None:
        """AC-002: source_id requires min_length=1."""
        with pytest.raises(ValidationError):
            self._make_envelope(source_id="")

    def test_missing_required_field_source_id(self) -> None:
        """AC-002: source_id is required."""
        with pytest.raises(ValidationError):
            MessageEnvelope(
                event_type=EventType.BUILD_STARTED,
                payload={"key": "value"},
            )  # type: ignore[call-arg]

    def test_missing_required_field_event_type(self) -> None:
        """AC-002: event_type is required."""
        with pytest.raises(ValidationError):
            MessageEnvelope(
                source_id="test-agent",
                payload={"key": "value"},
            )  # type: ignore[call-arg]

    def test_missing_required_field_payload(self) -> None:
        """AC-002: payload is required."""
        with pytest.raises(ValidationError):
            MessageEnvelope(
                source_id="test-agent",
                event_type=EventType.BUILD_STARTED,
            )  # type: ignore[call-arg]


class TestMessageEnvelopeConfig:
    """Verify model config and serialization behavior."""

    def test_extra_fields_ignored(self) -> None:
        """AC-003: model_config extra='ignore' for forward compatibility."""
        env = MessageEnvelope(
            source_id="test-agent",
            event_type=EventType.BUILD_STARTED,
            payload={"key": "value"},
            unknown_future_field="should be ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(env, "unknown_future_field")

    def test_json_serialisation_iso8601_timestamp(self) -> None:
        """AC-005: JSON serialisation uses ISO 8601 for timestamps."""
        env = make_envelope()
        json_str = env.model_dump_json()
        data = json.loads(json_str)
        ts = data["timestamp"]
        parsed = datetime.fromisoformat(ts)
        assert parsed is not None

    def test_json_roundtrip(self) -> None:
        """MessageEnvelope can serialize to JSON and deserialize back."""
        env = make_envelope()
        json_str = env.model_dump_json()
        restored = MessageEnvelope.model_validate_json(json_str)
        assert restored.message_id == env.message_id
        assert restored.source_id == env.source_id
        assert restored.event_type == env.event_type
        assert restored.payload == env.payload

    def test_all_fields_have_descriptions(self) -> None:
        """AC-004: All fields must have Field(description=...)."""
        for name, field_info in MessageEnvelope.model_fields.items():
            assert field_info.description is not None, (
                f"Field '{name}' is missing description"
            )
            assert len(field_info.description) > 0, (
                f"Field '{name}' has empty description"
            )


class TestPayloadClassForEventType:
    """Verify payload_class_for_event_type helper function."""

    def test_returns_payload_class_for_registered_event_type(self) -> None:
        """AC-006: payload_class_for_event_type returns the correct class."""
        from nats_core.envelope import payload_class_for_event_type

        cls = payload_class_for_event_type(EventType.BUILD_STARTED)
        assert cls is not None
        assert hasattr(cls, "model_fields")


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


# ===========================================================================
# TASK-ME03: BDD scenario tests (23 scenarios)
# ===========================================================================


class TestBddSmoke:
    """BDD Smoke tests (4 scenarios): defaults, serialise, deserialise, unknown fields."""

    @pytest.mark.smoke
    @pytest.mark.key_example
    def test_creating_envelope_with_defaults(self) -> None:
        """BDD: Creating an envelope with defaults.

        - message_id should be a valid UUID v4
        - timestamp should be within 1 second of now in UTC
        - version should be "1.0"
        """
        now = datetime.now(timezone.utc)
        env = make_envelope()

        # message_id is a valid UUID v4
        parsed_uuid = UUID(env.message_id, version=4)
        assert str(parsed_uuid) == env.message_id

        # timestamp within 1 second of now
        delta = abs((env.timestamp - now).total_seconds())
        assert delta < 1.0, f"Timestamp drift {delta}s exceeds 1s tolerance"

        # version default
        assert env.version == "1.0"

    @pytest.mark.smoke
    @pytest.mark.key_example
    def test_serialising_envelope_to_json(self) -> None:
        """BDD: Serialising an envelope to JSON.

        - output should be valid JSON
        - timestamp should be in ISO 8601 format
        - all fields should be present in the output
        """
        env = make_envelope(correlation_id="corr-1", project="proj-1")
        raw = env.model_dump_json()
        data = json.loads(raw)

        # Valid JSON (implicitly tested by json.loads succeeding)
        assert isinstance(data, dict)

        # Timestamp is ISO 8601
        datetime.fromisoformat(data["timestamp"])

        # All fields present
        expected_fields = {
            "message_id",
            "timestamp",
            "version",
            "source_id",
            "event_type",
            "project",
            "correlation_id",
            "payload",
        }
        assert expected_fields == set(data.keys())

    @pytest.mark.smoke
    @pytest.mark.key_example
    def test_deserialising_envelope_from_valid_json(self) -> None:
        """BDD: Deserialising an envelope from valid JSON.

        - all fields should match the original values
        - message_id should be preserved exactly
        - timestamp should be preserved exactly
        """
        original = make_envelope(correlation_id="sess-42", project="myproj")
        raw = original.model_dump_json()
        restored = MessageEnvelope.model_validate_json(raw)

        assert restored.message_id == original.message_id
        assert restored.timestamp == original.timestamp
        assert restored.version == original.version
        assert restored.source_id == original.source_id
        assert restored.event_type == original.event_type
        assert restored.project == original.project
        assert restored.correlation_id == original.correlation_id
        assert restored.payload == original.payload

    @pytest.mark.smoke
    @pytest.mark.negative
    def test_deserialising_with_unknown_fields_ignores_them(self) -> None:
        """BDD: Deserialising with unknown fields ignores them silently.

        - it should parse without error
        - the unknown field should not appear in the model
        """
        base = make_envelope()
        data = json.loads(base.model_dump_json())
        data["future_field"] = "some_value"
        raw = json.dumps(data)

        restored = MessageEnvelope.model_validate_json(raw)
        assert not hasattr(restored, "future_field")
        assert restored.source_id == base.source_id


class TestBddKeyExample:
    """BDD Key-example tests (5 scenarios): defaults, serialise, deserialise,
    correlation, project scope.

    Note: 3 of 5 are in TestBddSmoke (dual-tagged). The 2 remaining are here.
    """

    @pytest.mark.key_example
    def test_correlation_id_links_related_messages(self) -> None:
        """BDD: Correlation ID links related messages.

        - both envelopes should share the same correlation_id
        - they should have different message_ids
        - they should have different timestamps
        """
        corr = "session-abc-123"
        env1 = make_envelope(correlation_id=corr)
        time.sleep(0.002)
        env2 = make_envelope(correlation_id=corr)

        assert env1.correlation_id == corr
        assert env2.correlation_id == corr
        assert env1.message_id != env2.message_id
        assert env1.timestamp != env2.timestamp

    @pytest.mark.key_example
    def test_creating_envelope_with_project_scope(self) -> None:
        """BDD: Creating an envelope with a project scope.

        - the project field should be "finproxy"
        - all other default fields should still be populated
        """
        env = make_envelope(project="finproxy", source_id="guardkit-factory")

        assert env.project == "finproxy"
        assert env.source_id == "guardkit-factory"
        # Default fields populated
        assert env.message_id
        assert env.timestamp is not None
        assert env.version == "1.0"
        assert env.event_type == EventType.STATUS
        assert env.payload == {"key": "value"}


class TestBddBoundary:
    """BDD Boundary tests (6 scenarios): version, empty source_id, invalid event_type,
    optional None fields (x2), empty payload, unique message_ids.
    """

    @pytest.mark.boundary
    def test_version_field_accepts_current_version(self) -> None:
        """BDD: Version field accepts the current version string."""
        env = make_envelope(version="1.0")
        assert env.version == "1.0"

    @pytest.mark.boundary
    @pytest.mark.negative
    def test_empty_source_id_is_rejected(self) -> None:
        """BDD: Empty source_id is rejected.

        - it should raise a validation error
        - the error should indicate source_id must not be empty
        """
        with pytest.raises(ValidationError) as exc_info:
            MessageEnvelope(
                source_id="",
                event_type=EventType.STATUS,
                payload={},
            )
        errors = exc_info.value.errors()
        source_id_errors = [e for e in errors if "source_id" in str(e.get("loc", ()))]
        assert len(source_id_errors) > 0

    @pytest.mark.boundary
    @pytest.mark.negative
    def test_invalid_event_type_is_rejected(self) -> None:
        """BDD: Invalid event_type is rejected.

        - it should raise a validation error
        - the error should indicate the event type is not valid
        """
        with pytest.raises(ValidationError) as exc_info:
            MessageEnvelope(
                source_id="test-agent",
                event_type="nonexistent_event",  # type: ignore[arg-type]
                payload={},
            )
        errors = exc_info.value.errors()
        event_type_errors = [e for e in errors if "event_type" in str(e.get("loc", ()))]
        assert len(event_type_errors) > 0

    @pytest.mark.boundary
    @pytest.mark.parametrize("field_name", ["project", "correlation_id"])
    def test_optional_fields_accept_none(self, field_name: str) -> None:
        """BDD: Optional fields accept None.

        Scenario Outline with project and correlation_id.
        """
        env = make_envelope(**{field_name: None})
        assert getattr(env, field_name) is None

    @pytest.mark.boundary
    def test_envelope_accepts_empty_payload(self) -> None:
        """BDD: Envelope accepts an empty payload dictionary.

        - the envelope should be valid
        - the payload should be an empty dictionary
        """
        env = make_envelope(payload={})
        assert env.payload == {}

    @pytest.mark.boundary
    def test_each_envelope_generates_unique_message_id(self) -> None:
        """BDD: Each envelope generates a unique message_id by default.

        Create 100 envelopes and verify all message_ids are unique.
        """
        ids = [make_envelope().message_id for _ in range(100)]
        assert len(set(ids)) == 100


class TestBddNegative:
    """BDD Negative tests (4 scenarios): unknown fields (in smoke), missing source_id,
    missing event_type, missing payload.

    Note: 'unknown fields' scenario is in TestBddSmoke (dual-tagged).
    """

    @pytest.mark.negative
    def test_missing_source_id_raises_validation_error(self) -> None:
        """BDD: Missing required source_id raises a validation error.

        - it should raise a validation error
        - the error should mention source_id
        """
        data = json.loads(make_envelope_json())
        del data["source_id"]
        raw = json.dumps(data)

        with pytest.raises(ValidationError) as exc_info:
            MessageEnvelope.model_validate_json(raw)
        error_text = str(exc_info.value)
        assert "source_id" in error_text

    @pytest.mark.negative
    def test_missing_event_type_raises_validation_error(self) -> None:
        """BDD: Missing required event_type raises a validation error.

        - it should raise a validation error
        - the error should mention event_type
        """
        data = json.loads(make_envelope_json())
        del data["event_type"]
        raw = json.dumps(data)

        with pytest.raises(ValidationError) as exc_info:
            MessageEnvelope.model_validate_json(raw)
        error_text = str(exc_info.value)
        assert "event_type" in error_text

    @pytest.mark.negative
    def test_missing_payload_raises_validation_error(self) -> None:
        """BDD: Missing required payload raises a validation error.

        - it should raise a validation error
        - the error should mention payload
        """
        data = json.loads(make_envelope_json())
        del data["payload"]
        raw = json.dumps(data)

        with pytest.raises(ValidationError) as exc_info:
            MessageEnvelope.model_validate_json(raw)
        error_text = str(exc_info.value)
        assert "payload" in error_text


class TestBddEdgeCase:
    """BDD Edge-case tests (8 scenarios)."""

    @pytest.mark.edge_case
    def test_large_payload_without_truncation(self) -> None:
        """BDD: Envelope handles a large payload without truncation.

        50 keys with nested structures round-trip exactly.
        """
        large_payload: dict[str, object] = {
            f"key_{i}": {
                "nested": f"value_{i}",
                "list": list(range(10)),
                "deep": {"a": i, "b": [True, False, None]},
            }
            for i in range(50)
        }
        env = make_envelope(payload=large_payload)
        raw = env.model_dump_json()
        restored = MessageEnvelope.model_validate_json(raw)

        assert restored.payload == large_payload

    @pytest.mark.edge_case
    def test_explicit_message_id_and_timestamp_override_defaults(self) -> None:
        """BDD: Explicit message_id and timestamp override defaults.

        - message_id should be "custom-id-12345"
        - timestamp should be 2026-01-15T10:30:00Z
        """
        ts = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        env = make_envelope(message_id="custom-id-12345", timestamp=ts)

        assert env.message_id == "custom-id-12345"
        assert env.timestamp == ts

    @pytest.mark.edge_case
    def test_future_version_string_round_trips(self) -> None:
        """BDD: Future version string round-trips correctly.

        - version should be "2.0" after round-trip
        """
        env = make_envelope(version="2.0")
        raw = env.model_dump_json()
        restored = MessageEnvelope.model_validate_json(raw)

        assert restored.version == "2.0"

    @pytest.mark.edge_case
    def test_correlation_id_propagates_through_chain(self) -> None:
        """BDD: Correlation ID propagates through a chain of messages.

        - all three should have correlation_id "chain-001"
        - all three should have distinct message_ids
        - all three should have distinct timestamps
        """
        corr = "chain-001"
        envelopes = []
        for _ in range(3):
            envelopes.append(make_envelope(correlation_id=corr))
            time.sleep(0.002)

        assert all(e.correlation_id == corr for e in envelopes)
        ids = [e.message_id for e in envelopes]
        assert len(set(ids)) == 3
        timestamps = [e.timestamp for e in envelopes]
        assert len(set(timestamps)) == 3

    @pytest.mark.edge_case
    def test_non_ascii_payload_round_trips(self) -> None:
        """BDD: Payload with non-ASCII characters round-trips correctly.

        Includes emoji, CJK text, and accented characters.
        """
        payload: dict[str, str] = {
            "greeting": "Hello, world! \u2764\ufe0f",
            "emoji": "\U0001f680\U0001f31f\U0001f525",
            "cjk": "\u4f60\u597d\u4e16\u754c \u3053\u3093\u306b\u3061\u306f",
            "accented": "caf\u00e9 na\u00efve r\u00e9sum\u00e9",
        }
        env = make_envelope(payload=payload)
        raw = env.model_dump_json()
        restored = MessageEnvelope.model_validate_json(raw)

        assert restored.payload == payload

    @pytest.mark.edge_case
    async def test_concurrent_envelope_creation_no_collisions(self) -> None:
        """BDD: Concurrent envelope creation produces no message_id collisions.

        Create 1000 envelopes concurrently and verify all IDs are unique.
        """

        async def _create_envelope() -> str:
            return make_envelope().message_id

        tasks = [_create_envelope() for _ in range(1000)]
        ids = await asyncio.gather(*tasks)

        assert len(set(ids)) == 1000

    @pytest.mark.edge_case
    def test_datetime_payload_serialises_consistently(self) -> None:
        """BDD: Payload containing datetime values serialises them consistently.

        Datetime stored as an ISO 8601 string in the payload is preserved.
        """
        dt_string = "2026-03-15T14:30:00Z"
        payload: dict[str, str] = {"event_time": dt_string, "label": "start"}
        env = make_envelope(payload=payload)
        raw = env.model_dump_json()
        restored = MessageEnvelope.model_validate_json(raw)

        assert restored.payload["event_time"] == dt_string

    @pytest.mark.edge_case
    def test_cross_version_envelope_parses_successfully(self) -> None:
        """BDD: Envelope from a different library version parses successfully.

        JSON with extra unknown fields and missing optional fields should parse.
        """
        data: dict[str, object] = {
            "message_id": "cross-ver-001",
            "timestamp": "2026-01-01T00:00:00Z",
            "version": "1.5",
            "source_id": "legacy-agent",
            "event_type": "status",
            "payload": {"data": "test"},
            # Extra unknown fields from a future version
            "priority": "high",
            "trace_id": "abc-123",
        }
        # project and correlation_id intentionally missing (optional)
        raw = json.dumps(data)
        env = MessageEnvelope.model_validate_json(raw)

        # Known required fields present
        assert env.message_id == "cross-ver-001"
        assert env.source_id == "legacy-agent"
        assert env.event_type == EventType.STATUS
        assert env.payload == {"data": "test"}
        assert env.version == "1.5"

        # Optional fields default to None when missing
        assert env.project is None
        assert env.correlation_id is None

        # Unknown fields silently ignored
        assert not hasattr(env, "priority")
        assert not hasattr(env, "trace_id")
