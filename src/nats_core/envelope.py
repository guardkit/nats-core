"""EventType enum and MessageEnvelope model for NATS message wire format.

Defines the canonical wire format for all NATS messages in the fleet.
See DM-message-contracts.md for field specifications and
ADR-002-schema-versioning.md for forward-compatibility rationale.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    """Enumeration of all event types across fleet domains.

    Covers four domains: Pipeline, Agent, Jarvis, and Fleet.
    Each value is a lowercase snake_case string suitable for use
    as a NATS subject segment.
    """

    # Pipeline domain (6)
    FEATURE_PLANNED = "feature_planned"
    FEATURE_READY_FOR_BUILD = "feature_ready_for_build"
    BUILD_STARTED = "build_started"
    BUILD_PROGRESS = "build_progress"
    BUILD_COMPLETE = "build_complete"
    BUILD_FAILED = "build_failed"

    # Agent domain (6)
    STATUS = "status"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    COMMAND = "command"
    RESULT = "result"
    ERROR = "error"

    # Jarvis domain (4)
    INTENT_CLASSIFIED = "intent_classified"
    DISPATCH = "dispatch"
    AGENT_RESULT = "agent_result"
    NOTIFICATION = "notification"

    # Fleet domain (3)
    AGENT_REGISTER = "agent_register"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_DEREGISTER = "agent_deregister"


class MessageEnvelope(BaseModel):
    """Canonical wire-format envelope for all NATS messages in the fleet.

    Every message published to NATS is wrapped in this envelope so that
    consumers can route, correlate, and version-check without inspecting
    the inner payload.

    Attributes:
        message_id: Globally unique identifier for this message.
        timestamp: UTC creation time in ISO 8601 format.
        version: Schema version of the envelope format.
        source_id: Identifier of the agent or service that produced the message.
        event_type: Categorises the message for routing and dispatch.
        project: Optional project scope for multi-project deployments.
        correlation_id: Optional identifier linking related messages.
        payload: Arbitrary JSON-serialisable data carried by the message.
    """

    model_config = ConfigDict(extra="ignore")

    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Globally unique identifier for this message",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation time in ISO 8601 format",
    )
    version: str = Field(
        default="1.0",
        description="Schema version of the envelope format",
    )
    source_id: str = Field(
        min_length=1,
        description="Identifier of the agent or service that produced the message",
    )
    event_type: EventType = Field(
        description="Categorises the message for routing and dispatch",
    )
    project: str | None = Field(
        default=None,
        description="Optional project scope for multi-project deployments",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional identifier linking related messages",
    )
    payload: dict[str, Any] = Field(
        description="Arbitrary JSON-serialisable data carried by the message",
    )


def payload_class_for_event_type(event_type: EventType) -> type[BaseModel]:
    """Return the Pydantic model class for the given event type's payload.

    This is a forward-looking hook that will be implemented once per-event
    payload models are defined. For now it raises ``NotImplementedError``.

    Args:
        event_type: The event type whose payload class is requested.

    Raises:
        NotImplementedError: Always, until per-event payload models exist.
    """
    msg = (
        f"Payload model for event type '{event_type.value}' is not yet implemented. "
        "Per-event payload models will be added in a future task."
    )
    raise NotImplementedError(msg)
