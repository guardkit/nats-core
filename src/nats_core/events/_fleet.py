"""Fleet domain event payloads for agent heartbeat and deregistration.

Defines ``AgentHeartbeatPayload`` and ``AgentDeregistrationPayload`` used
by the fleet management subsystem.  ``AgentDeregistrationPayload`` enforces
kebab-case ``agent_id`` format (ASSUM-008).

Note: The agent *registration* payload is ``AgentManifest`` in
``nats_core.manifest`` per DDR-002.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentHeartbeatPayload(BaseModel):
    """Periodic heartbeat published by a running agent.

    Attributes:
        agent_id: Identifier of the agent sending the heartbeat.
        status: Current operational status of the agent.
        queue_depth: Number of tasks waiting in the agent's queue.
        active_tasks: Number of tasks currently being processed.
        uptime_seconds: Total seconds since the agent started.
        last_task_completed_at: UTC timestamp of the most recently completed task.
        active_workflow_states: Map of workflow ID to current state label.
    """

    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(description="Identifier of the agent sending the heartbeat")
    status: Literal["ready", "busy", "degraded", "draining"] = Field(
        description="Current operational status of the agent",
    )
    queue_depth: int = Field(
        default=0,
        ge=0,
        description="Number of tasks waiting in the agent's queue",
    )
    active_tasks: int = Field(
        default=0,
        ge=0,
        description="Number of tasks currently being processed",
    )
    uptime_seconds: int = Field(
        ge=0,
        description="Total seconds since the agent started",
    )
    last_task_completed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of the most recently completed task",
    )
    active_workflow_states: dict[str, str] = Field(
        default_factory=dict,
        description="Map of workflow ID to current state label",
    )


class AgentDeregistrationPayload(BaseModel):
    """Payload published when an agent leaves the fleet.

    Attributes:
        agent_id: Kebab-case identifier of the departing agent (ASSUM-008).
        reason: Human-readable reason for deregistration.
    """

    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(
        pattern=r"^[a-z][a-z0-9-]*$",
        description="Kebab-case agent identifier",
    )
    reason: str = Field(
        default="shutdown",
        description="Human-readable reason for deregistration",
    )
