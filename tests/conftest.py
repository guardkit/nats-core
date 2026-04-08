"""Shared test fixtures and factory functions for nats-core tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nats_core.envelope import EventType, MessageEnvelope


@dataclass
class MockEnvelopeData:
    """Mock data for MessageEnvelope construction."""

    source: str = "test-agent"
    event_type: str = "test.event"
    payload: dict[str, str] = field(default_factory=lambda: {"key": "value"})
    version: str = "1.0.0"


def make_envelope_data(**overrides: object) -> MockEnvelopeData:
    """Create a MockEnvelopeData with optional field overrides.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A MockEnvelopeData instance with the given overrides applied.
    """
    defaults: dict[str, object] = {
        "source": "test-agent",
        "event_type": "test.event",
        "payload": {"key": "value"},
        "version": "1.0.0",
    }
    defaults.update(overrides)
    return MockEnvelopeData(**defaults)  # type: ignore[arg-type]


def make_envelope(**overrides: Any) -> MessageEnvelope:
    """Create a MessageEnvelope with sensible defaults and optional overrides.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A MessageEnvelope instance with defaults for source_id, event_type,
        and payload, plus any caller-specified overrides.
    """
    defaults: dict[str, Any] = {
        "source_id": "test-agent",
        "event_type": EventType.STATUS,
        "payload": {"key": "value"},
    }
    defaults.update(overrides)
    return MessageEnvelope(**defaults)


def make_envelope_json(**overrides: Any) -> str:
    """Create a JSON string representing a MessageEnvelope with sensible defaults.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A JSON string that can be parsed as a MessageEnvelope.
    """
    envelope = make_envelope(**overrides)
    return envelope.model_dump_json()


# ---------------------------------------------------------------------------
# Topic Registry test helpers
# ---------------------------------------------------------------------------


def make_valid_feature_id(**overrides: str) -> str:
    """Create a valid feature ID string for topic resolution tests.

    Args:
        **overrides: Provide ``feature_id`` to override the default.

    Returns:
        A feature ID string safe for use in topic resolution.
    """
    return overrides.get("feature_id", "FEAT-001")


def make_valid_agent_id(**overrides: str) -> str:
    """Create a valid agent ID string for topic resolution tests.

    Args:
        **overrides: Provide ``agent_id`` to override the default.

    Returns:
        An agent ID string safe for use in topic resolution.
    """
    return overrides.get("agent_id", "guardkit-factory")
