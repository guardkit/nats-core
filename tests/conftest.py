"""Shared test fixtures and factory functions for nats-core tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nats_core.agent_config import AgentConfig, GraphitiConfig, ModelConfig
from nats_core.config import NATSConfig
from nats_core.envelope import EventType, MessageEnvelope
from nats_core.manifest import (
    AgentManifest,
    InMemoryManifestRegistry,
    IntentCapability,
    ToolCapability,
)

# ---------------------------------------------------------------------------
# NATSConfig test helpers
# ---------------------------------------------------------------------------


def make_nats_config(**overrides: Any) -> NATSConfig:
    """Create a NATSConfig with sensible defaults and optional overrides.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A NATSConfig instance with defaults plus any caller-specified overrides.
    """
    return NATSConfig(**overrides)


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


# ---------------------------------------------------------------------------
# AgentConfig test helpers
# ---------------------------------------------------------------------------


def make_model_config(**overrides: Any) -> ModelConfig:
    """Create a ModelConfig with sensible defaults and optional overrides.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A ModelConfig instance with defaults plus any caller-specified overrides.
    """
    defaults: dict[str, Any] = {"reasoning_model": "gpt-4"}
    defaults.update(overrides)
    return ModelConfig(**defaults)


def make_graphiti_config(**overrides: Any) -> GraphitiConfig:
    """Create a GraphitiConfig with sensible defaults and optional overrides.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A GraphitiConfig instance with defaults plus any caller-specified overrides.
    """
    return GraphitiConfig(**overrides)


def make_agent_config(**overrides: Any) -> AgentConfig:
    """Create an AgentConfig with sensible defaults and optional overrides.

    The ``models`` field is required and defaults to a ModelConfig with
    ``reasoning_model="gpt-4"`` if not explicitly provided.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        An AgentConfig instance with defaults plus any caller-specified overrides.
    """
    defaults: dict[str, Any] = {"models": make_model_config()}
    defaults.update(overrides)
    return AgentConfig(**defaults)


# ---------------------------------------------------------------------------
# Manifest & Registry test helpers
# ---------------------------------------------------------------------------


def make_intent_capability(**overrides: Any) -> IntentCapability:
    """Create an IntentCapability with sensible defaults and optional overrides.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        An IntentCapability instance with defaults plus any caller-specified overrides.
    """
    defaults: dict[str, Any] = {
        "pattern": "software.*",
        "description": "Handles software-related intents",
    }
    defaults.update(overrides)
    return IntentCapability(**defaults)


def make_tool_capability(**overrides: Any) -> ToolCapability:
    """Create a ToolCapability with sensible defaults and optional overrides.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        A ToolCapability instance with defaults plus any caller-specified overrides.
    """
    defaults: dict[str, Any] = {
        "name": "lint",
        "description": "Run code linting",
        "parameters": {"type": "object"},
        "returns": "Lint report",
    }
    defaults.update(overrides)
    return ToolCapability(**defaults)


def make_agent_manifest(**overrides: Any) -> AgentManifest:
    """Create an AgentManifest with sensible defaults and optional overrides.

    Args:
        **overrides: Keyword arguments to override default field values.

    Returns:
        An AgentManifest instance with defaults plus any caller-specified overrides.
    """
    defaults: dict[str, Any] = {
        "agent_id": "test-agent",
        "name": "Test Agent",
        "template": "basic",
    }
    defaults.update(overrides)
    return AgentManifest(**defaults)


def make_in_memory_registry() -> InMemoryManifestRegistry:
    """Create an empty InMemoryManifestRegistry.

    Returns:
        A fresh InMemoryManifestRegistry with no registered manifests.
    """
    return InMemoryManifestRegistry()
