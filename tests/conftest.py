"""Shared test fixtures and factory functions for nats-core tests."""

from __future__ import annotations

from dataclasses import dataclass, field


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
