"""nats-core: Shared contract layer for the Jarvis Ship's Computer fleet."""

from __future__ import annotations

from nats_core.agent_config import AgentConfig, GraphitiConfig, ModelConfig
from nats_core.client import NATSClient, NATSKVManifestRegistry
from nats_core.config import NATSConfig
from nats_core.envelope import EventType, MessageEnvelope, payload_class_for_event_type
from nats_core.manifest import (
    AgentManifest,
    InMemoryManifestRegistry,
    IntentCapability,
    ManifestRegistry,
    ToolCapability,
)
from nats_core.topics import Topics

__version__ = "0.1.0"

__all__ = [
    "AgentConfig",
    "AgentManifest",
    "EventType",
    "GraphitiConfig",
    "InMemoryManifestRegistry",
    "IntentCapability",
    "ManifestRegistry",
    "MessageEnvelope",
    "ModelConfig",
    "NATSClient",
    "NATSConfig",
    "NATSKVManifestRegistry",
    "ToolCapability",
    "Topics",
    "__version__",
    "payload_class_for_event_type",
]
