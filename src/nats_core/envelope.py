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

from nats_core.events._agent import (
    AgentStatusPayload,
    ApprovalRequestPayload,
    ApprovalResponsePayload,
    CommandPayload,
    ResultPayload,
)
from nats_core.events._fleet import AgentDeregistrationPayload, AgentHeartbeatPayload
from nats_core.events._jarvis import (
    AgentResultPayload,
    DispatchPayload,
    IntentClassifiedPayload,
    NotificationPayload,
)
from nats_core.events._pipeline import (
    BuildCancelledPayload,
    BuildCompletePayload,
    BuildFailedPayload,
    BuildPausedPayload,
    BuildProgressPayload,
    BuildQueuedPayload,
    BuildResumedPayload,
    BuildStartedPayload,
    FeaturePlannedPayload,
    FeatureReadyForBuildPayload,
    StageCompletePayload,
    StageGatedPayload,
)
from nats_core.manifest import AgentManifest


class EventType(str, Enum):
    """Enumeration of all event types across fleet domains.

    Covers four domains: Pipeline, Agent, Jarvis, and Fleet.
    Each value is a lowercase snake_case string suitable for use
    as a NATS subject segment.
    """

    # Pipeline domain (12)
    FEATURE_PLANNED = "feature_planned"
    FEATURE_READY_FOR_BUILD = "feature_ready_for_build"
    BUILD_QUEUED = "build_queued"
    BUILD_STARTED = "build_started"
    BUILD_PROGRESS = "build_progress"
    BUILD_PAUSED = "build_paused"
    BUILD_RESUMED = "build_resumed"
    BUILD_CANCELLED = "build_cancelled"
    BUILD_COMPLETE = "build_complete"
    BUILD_FAILED = "build_failed"
    STAGE_COMPLETE = "stage_complete"
    STAGE_GATED = "stage_gated"

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


# Module-level registry mapping every EventType member to its payload class.
# ERROR reuses AgentStatusPayload (with state="error") per the agent domain spec.
_EVENT_TYPE_REGISTRY: dict[EventType, type[BaseModel]] = {
    # Pipeline domain
    EventType.FEATURE_PLANNED: FeaturePlannedPayload,
    EventType.FEATURE_READY_FOR_BUILD: FeatureReadyForBuildPayload,
    EventType.BUILD_QUEUED: BuildQueuedPayload,
    EventType.BUILD_STARTED: BuildStartedPayload,
    EventType.BUILD_PROGRESS: BuildProgressPayload,
    EventType.BUILD_PAUSED: BuildPausedPayload,
    EventType.BUILD_RESUMED: BuildResumedPayload,
    EventType.BUILD_CANCELLED: BuildCancelledPayload,
    EventType.BUILD_COMPLETE: BuildCompletePayload,
    EventType.BUILD_FAILED: BuildFailedPayload,
    EventType.STAGE_COMPLETE: StageCompletePayload,
    EventType.STAGE_GATED: StageGatedPayload,
    # Agent domain
    EventType.STATUS: AgentStatusPayload,
    EventType.APPROVAL_REQUEST: ApprovalRequestPayload,
    EventType.APPROVAL_RESPONSE: ApprovalResponsePayload,
    EventType.COMMAND: CommandPayload,
    EventType.RESULT: ResultPayload,
    EventType.ERROR: AgentStatusPayload,
    # Jarvis domain
    EventType.INTENT_CLASSIFIED: IntentClassifiedPayload,
    EventType.DISPATCH: DispatchPayload,
    EventType.AGENT_RESULT: AgentResultPayload,
    EventType.NOTIFICATION: NotificationPayload,
    # Fleet domain
    EventType.AGENT_REGISTER: AgentManifest,
    EventType.AGENT_HEARTBEAT: AgentHeartbeatPayload,
    EventType.AGENT_DEREGISTER: AgentDeregistrationPayload,
}


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

    Looks up the payload class from the module-level ``_EVENT_TYPE_REGISTRY``
    dictionary. Every ``EventType`` member has a registered class.

    Args:
        event_type: The event type whose payload class is requested.

    Returns:
        The Pydantic ``BaseModel`` subclass for the given event type.

    Raises:
        KeyError: If ``event_type`` is not registered in the registry.
    """
    try:
        return _EVENT_TYPE_REGISTRY[event_type]
    except KeyError:
        msg = f"No payload class registered for event type '{event_type.value}'"
        raise KeyError(msg) from None
