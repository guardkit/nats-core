"""Event type schemas for the nats-core contract layer."""

from __future__ import annotations

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
    BuildCompletePayload,
    BuildFailedPayload,
    BuildProgressPayload,
    BuildStartedPayload,
    FeaturePlannedPayload,
    FeatureReadyForBuildPayload,
    TaskProgress,
    WaveSummary,
)

__all__ = [
    "AgentDeregistrationPayload",
    "AgentHeartbeatPayload",
    "AgentResultPayload",
    "AgentStatusPayload",
    "ApprovalRequestPayload",
    "ApprovalResponsePayload",
    "BuildCompletePayload",
    "BuildFailedPayload",
    "BuildProgressPayload",
    "BuildStartedPayload",
    "CommandPayload",
    "DispatchPayload",
    "FeaturePlannedPayload",
    "FeatureReadyForBuildPayload",
    "IntentClassifiedPayload",
    "NotificationPayload",
    "ResultPayload",
    "TaskProgress",
    "WaveSummary",
]
