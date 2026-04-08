"""nats-core: Shared contract layer for the Jarvis Ship's Computer fleet."""

from __future__ import annotations

from nats_core.envelope import EventType, MessageEnvelope, payload_class_for_event_type

__version__ = "0.1.0"

__all__ = [
    "EventType",
    "MessageEnvelope",
    "__version__",
    "payload_class_for_event_type",
]
