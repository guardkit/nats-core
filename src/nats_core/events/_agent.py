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

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Disposition vocabulary and the UX/bus-verb synonym map for per-assumption
# dispositions (WS1 Session I item 5; backward-edge episode schema contract
# 2026-07-07 §4.1 / §7 item 1). The canonical values match the fleet-memory
# ``planning_outcome.assumptions[].disposition`` vocabulary verbatim;
# ``undecided`` (a run terminated before an assumption was decided) is included
# for round-trip parity but is not part of the synonym map — it is never a
# human submission.
Disposition = Literal["accepted", "modified", "rejected", "deferred", "undecided"]

# UX/bus verb -> contract value (§4.1 "Disposition synonym map", binding on WS1-I):
#   approve -> accepted, edit -> modified, reject -> rejected, defer -> deferred.
_DISPOSITION_SYNONYMS: dict[str, str] = {
    "approve": "accepted",
    "edit": "modified",
    "reject": "rejected",
    "defer": "deferred",
}


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


class AssumptionDisposition(BaseModel):
    """One human decision on a single surfaced assumption.

    The structured, first-class replacement for the FEAT-SPL-003 ASSUM-003
    JSON-in-``notes`` bridge (WS1 Session I item 5). Every field maps verbatim
    onto the fleet-memory ``planning_outcome.assumptions[]`` entry
    (backward-edge episode schema contract §4.1), so the Mode P producer emits
    the structured block with no reshaping.

    ``disposition`` accepts the UX/bus verbs (``approve`` / ``edit`` /
    ``reject`` / ``defer``) and normalises them to the canonical vocabulary
    (``accepted`` / ``modified`` / ``rejected`` / ``deferred``) via the
    binding synonym map.

    Attributes:
        assumption_id: Identifier of the assumption being decided.
        disposition: Canonical disposition (synonyms are normalised on input).
        edit_delta: Replacement text / unified diff when modified, or None.
        notes: Optional free-text note for this specific assumption.
    """

    model_config = ConfigDict(extra="ignore")

    assumption_id: str = Field(
        min_length=1,
        description="Identifier of the assumption being decided",
    )
    disposition: Disposition = Field(
        description=(
            "Canonical disposition: accepted | modified | rejected | deferred | "
            "undecided. UX/bus verbs approve/edit/reject/defer are normalised on "
            "input."
        ),
    )
    edit_delta: str | None = Field(
        default=None,
        description="Replacement text / unified diff when modified, or None",
    )
    notes: str | None = Field(
        default=None,
        description="Optional free-text note for this specific assumption",
    )

    @field_validator("disposition", mode="before")
    @classmethod
    def _normalise_disposition(cls, v: Any) -> Any:
        if isinstance(v, str):
            return _DISPOSITION_SYNONYMS.get(v, v)
        return v


class ApprovalResponsePayload(BaseModel):
    """Payload for human-in-the-loop approval responses.

    Published on ``agents.approval.{agent_id}.{task_id}.response``
    to convey the human (or Jarvis) decision on an approval request.

    ``dispositions`` (WS1 Session I item 5) carries the structured
    per-assumption decisions for a planning-assumption checkpoint. It is
    OPTIONAL and defaults to ``None``: build/other gates omit it, and it
    supersedes the FEAT-SPL-003 ASSUM-003 JSON-in-``notes`` bridge without
    breaking it (``notes`` stays available, so a producer may populate either
    or both during the migration window).

    Attributes:
        request_id: Identifier of the approval request being answered.
        decision: The approval decision.
        decided_by: Identifier of the entity that made the decision.
        notes: Optional free-text notes explaining the decision.
        dispositions: Structured per-assumption decisions, or None.
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
    dispositions: list[AssumptionDisposition] | None = Field(
        default=None,
        description=(
            "Structured per-assumption decisions for a planning-assumption "
            "checkpoint (WS1-I item 5), or None. Supersedes the ASSUM-003 "
            "JSON-in-notes bridge without breaking it."
        ),
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
