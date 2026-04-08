"""Agent domain event payload schemas.

Covers agent lifecycle (status, error), human-in-the-loop approval flow
(request/response), and generic command/result messaging.

``Literal`` type constraints enforce the documented finite value sets for
``state``, ``risk_level``, and ``decision`` fields at Pydantic v2 parse time.

This is a private module; public names are re-exported from
``nats_core.events``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentStatusPayload(BaseModel):
    """Payload for agent status and error events.

    Published on ``agents.status.{agent_id}`` whenever an agent's
    lifecycle state changes.  The ``error`` event type reuses this
    model with ``state="error"`` and a populated ``error_message``.

    Attributes:
        agent_id: Identifier of the reporting agent.
        state: Current lifecycle state of the agent.
        task_id: Identifier of the task the agent is working on, if any.
        task_description: Human-readable description of the current task.
        error_message: Error details when ``state`` is ``"error"``.
    """

    model_config = ConfigDict(extra="ignore")

    agent_id: str = Field(
        min_length=1,
        description="Identifier of the reporting agent",
    )
    state: Literal["running", "idle", "awaiting_approval", "error", "paused"] = Field(
        description="Current lifecycle state of the agent",
    )
    task_id: str | None = Field(
        default=None,
        description="Identifier of the task the agent is working on, if any",
    )
    task_description: str | None = Field(
        default=None,
        description="Human-readable description of the current task",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details when state is 'error'",
    )


class ApprovalRequestPayload(BaseModel):
    """Payload for human-in-the-loop approval requests.

    Published on ``agents.approval.{agent_id}.{task_id}`` when an agent
    needs human (or Jarvis) authorisation before proceeding with a
    potentially risky action.

    Attributes:
        request_id: Unique identifier for this approval request.
        agent_id: Identifier of the agent requesting approval.
        action_description: Human-readable description of the proposed action.
        risk_level: Assessed risk level of the proposed action.
        details: Extensible metadata about the proposed action.
        timeout_seconds: Seconds before the request expires.
    """

    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(
        min_length=1,
        description="Unique identifier for this approval request",
    )
    agent_id: str = Field(
        min_length=1,
        description="Identifier of the agent requesting approval",
    )
    action_description: str = Field(
        min_length=1,
        description="Human-readable description of the proposed action",
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Assessed risk level of the proposed action",
    )
    details: dict[str, Any] = Field(
        description="Extensible metadata about the proposed action",
    )
    timeout_seconds: int = Field(
        default=300,
        ge=0,
        description="Seconds before the request expires",
    )


class ApprovalResponsePayload(BaseModel):
    """Payload for human-in-the-loop approval responses.

    Published on ``agents.approval.{agent_id}.{task_id}.response``
    to convey the human (or Jarvis) decision on an approval request.

    Attributes:
        request_id: Identifier of the approval request being answered.
        decision: The approval decision.
        decided_by: Identifier of the entity that made the decision.
        notes: Optional free-text notes explaining the decision.
    """

    model_config = ConfigDict(extra="ignore")

    request_id: str = Field(
        min_length=1,
        description="Identifier of the approval request being answered",
    )
    decision: Literal["approve", "reject", "defer", "override"] = Field(
        description="The approval decision",
    )
    decided_by: str = Field(
        min_length=1,
        description="Identifier of the entity that made the decision",
    )
    notes: str | None = Field(
        default=None,
        description="Optional free-text notes explaining the decision",
    )


class CommandPayload(BaseModel):
    """Payload for generic agent command messages.

    Published on ``agents.command.{agent_id}`` by Jarvis or adapters to
    instruct an agent to perform an action.

    Attributes:
        command: The command verb or name to execute.
        args: Key-value arguments for the command.
        correlation_id: Optional identifier linking this command to a response.
    """

    model_config = ConfigDict(extra="ignore")

    command: str = Field(
        min_length=1,
        description="The command verb or name to execute",
    )
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value arguments for the command",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional identifier linking this command to a response",
    )


class ResultPayload(BaseModel):
    """Payload for generic agent result messages.

    Published on ``agents.result.{agent_id}`` by any agent to report the
    outcome of a command execution.

    Attributes:
        command: The command verb or name that was executed.
        result: Key-value result data from the command execution.
        correlation_id: Optional identifier linking this result to the originating command.
        success: Whether the command completed successfully.
    """

    model_config = ConfigDict(extra="ignore")

    command: str = Field(
        min_length=1,
        description="The command verb or name that was executed",
    )
    result: dict[str, Any] = Field(
        description="Key-value result data from the command execution",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Optional identifier linking this result to the originating command",
    )
    success: bool = Field(
        description="Whether the command completed successfully",
    )
