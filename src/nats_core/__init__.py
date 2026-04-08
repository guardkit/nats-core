"""nats-core: Shared contract layer for the Jarvis Ship's Computer fleet."""

from __future__ import annotations

from nats_core.envelope import EventType, MessageEnvelope, payload_class_for_event_type
from nats_core.manifest import AgentManifest, IntentCapability, ToolCapability
from nats_core.topics import Topics

__version__ = "0.1.0"

__all__ = [
    "AgentManifest",
    "EventType",
    "IntentCapability",
    "MessageEnvelope",
    "ToolCapability",
    "Topics",
    "__version__",
    "payload_class_for_event_type",
]
