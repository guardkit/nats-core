"""Runbook event payload schemas for runbook execution lifecycle.

Covers the full lifecycle of a runbook execution:
started → step_started → step_result → runbook_complete,
plus escalated events for exception handling.

All models use ``ConfigDict(extra="ignore")`` for backward compatibility
and ``Field(description=...)`` on every field per nats-core conventions.

This is a private module; public names are re-exported from
``nats_core.events.__init__``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RunbookStartedPayload(BaseModel):
    """Payload emitted when a runbook execution begins.

    Attributes:
        runbook_id: Unique identifier for the runbook execution.
        target: Target service or resource for the runbook.
        step_count: Total number of steps in the runbook.
        correlation_id: Identifier linking related messages.
    """

    model_config = ConfigDict(extra="ignore")

    runbook_id: str = Field(description="Unique identifier for the runbook execution")
    target: str = Field(description="Target service or resource for the runbook")
    step_count: int = Field(ge=0, description="Total number of steps in the runbook")
    correlation_id: str = Field(description="Identifier linking related messages")


class StepStartedPayload(BaseModel):
    """Payload emitted when a runbook step begins execution.

    Attributes:
        runbook_id: Unique identifier for the runbook execution.
        sequence_index: 0-based index of the step within the runbook.
        step_type: Type of step being executed (e.g., http_request, script).
        correlation_id: Identifier linking related messages.
    """

    model_config = ConfigDict(extra="ignore")

    runbook_id: str = Field(description="Unique identifier for the runbook execution")
    sequence_index: int = Field(
        ge=0, description="0-based index of the step within the runbook"
    )
    step_type: str = Field(
        description="Type of step being executed (e.g., http_request, script)"
    )
    correlation_id: str = Field(description="Identifier linking related messages")


class StepResultPayload(BaseModel):
    """Payload emitted when a runbook step completes.

    Attributes:
        runbook_id: Unique identifier for the runbook execution.
        sequence_index: 0-based index of the step within the runbook.
        step_type: Type of step that was executed.
        status: Execution status (pending, running, passed, failed, awaiting_approval).
        result: JSON-serializable result data from the step, or None if no result.
        correlation_id: Identifier linking related messages.
    """

    model_config = ConfigDict(extra="ignore")

    runbook_id: str = Field(description="Unique identifier for the runbook execution")
    sequence_index: int = Field(
        ge=0, description="0-based index of the step within the runbook"
    )
    step_type: str = Field(description="Type of step that was executed")
    status: Literal["pending", "running", "passed", "failed", "awaiting_approval"] = (
        Field(
            description="Execution status (pending, running, passed, failed, awaiting_approval)"
        )
    )
    result: dict[str, Any] | None = Field(
        description="JSON-serializable result data from the step, or None if no result"
    )
    correlation_id: str = Field(description="Identifier linking related messages")


class RunbookCompletePayload(BaseModel):
    """Payload emitted when a runbook execution completes.

    Attributes:
        runbook_id: Unique identifier for the runbook execution.
        step_count: Total number of steps that were executed.
        correlation_id: Identifier linking related messages.
    """

    model_config = ConfigDict(extra="ignore")

    runbook_id: str = Field(description="Unique identifier for the runbook execution")
    step_count: int = Field(ge=0, description="Total number of steps that were executed")
    correlation_id: str = Field(description="Identifier linking related messages")


class EscalatedPayload(BaseModel):
    """Payload emitted when a runbook execution is escalated.

    Attributes:
        runbook_id: Unique identifier for the runbook execution.
        sequence_index: 0-based index of the step that triggered escalation.
        reason: Escalation reason (unknown_handler, step_failed, awaiting_approval).
        correlation_id: Identifier linking related messages.
    """

    model_config = ConfigDict(extra="ignore")

    runbook_id: str = Field(description="Unique identifier for the runbook execution")
    sequence_index: int = Field(
        ge=0, description="0-based index of the step that triggered escalation"
    )
    reason: Literal["unknown_handler", "step_failed", "awaiting_approval"] = Field(
        description="Escalation reason (unknown_handler, step_failed, awaiting_approval)"
    )
    correlation_id: str = Field(description="Identifier linking related messages")
