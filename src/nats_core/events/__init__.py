"""Event type schemas for the nats-core contract layer."""

from __future__ import annotations

from nats_core.events._agent import (
    AgentStatusPayload,
    ApprovalRequestPayload,
    ApprovalResponsePayload,
    AssumptionDisposition,
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
from nats_core.events._memory import MAX_EPISODE_BODY_BYTES, MemoryEpisodeV1
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
    PlanningCompletePayload,
    PlanningFailedPayload,
    PlanningQueuedPayload,
    PlanningStartedPayload,
    SpecReadyForBuildPayload,
    StageCompletePayload,
    StageGatedPayload,
    TaskProgress,
    WaveSummary,
)
from nats_core.events._runbook import (
    EscalatedPayload,
    RunbookCompletePayload,
    RunbookStartedPayload,
    StepResultPayload,
    StepStartedPayload,
)

__all__ = [
    "AgentDeregistrationPayload",
    "AgentHeartbeatPayload",
    "AgentResultPayload",
    "AgentStatusPayload",
    "ApprovalRequestPayload",
    "ApprovalResponsePayload",
    "AssumptionDisposition",
    "BuildCancelledPayload",
    "BuildCompletePayload",
    "BuildFailedPayload",
    "BuildPausedPayload",
    "BuildProgressPayload",
    "BuildQueuedPayload",
    "BuildResumedPayload",
    "BuildStartedPayload",
    "CommandPayload",
    "DispatchPayload",
    "EscalatedPayload",
    "FeaturePlannedPayload",
    "FeatureReadyForBuildPayload",
    "IntentClassifiedPayload",
    "MAX_EPISODE_BODY_BYTES",
    "MemoryEpisodeV1",
    "NotificationPayload",
    "PlanningCompletePayload",
    "PlanningFailedPayload",
    "PlanningQueuedPayload",
    "PlanningStartedPayload",
    "ResultPayload",
    "SpecReadyForBuildPayload",
    "RunbookCompletePayload",
    "RunbookStartedPayload",
    "StageCompletePayload",
    "StageGatedPayload",
    "StepResultPayload",
    "StepStartedPayload",
    "TaskProgress",
    "WaveSummary",
]
