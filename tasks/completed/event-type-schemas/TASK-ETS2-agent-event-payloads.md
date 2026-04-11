---
id: TASK-ETS2
title: Implement agent event payload schemas
status: completed
task_type: declarative
parent_review: TASK-ETS0
feature_id: FEAT-ETS
wave: 1
implementation_mode: task-work
complexity: 3
dependencies:
- TASK-ME01
- TASK-ME02
priority: high
tags:
- pydantic
- events
- agent
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-310F
  base_branch: main
  started_at: '2026-04-08T19:58:25.415954'
  last_updated: '2026-04-08T20:05:16.316373'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T19:58:25.415954'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/event-type-schemas/
---

# Task: Implement agent event payload schemas

## Description

Implement the 5 agent event payload classes in `src/nats_core/events/_agent.py`.
These cover agent lifecycle (status, error), human-in-the-loop approval flow
(request/response), and generic command/result messaging.

`Literal` type constraints enforce the documented finite value sets for `state`,
`risk_level`, and `decision` fields.

## Acceptance Criteria

- [ ] `src/nats_core/events/_agent.py` created with `from __future__ import annotations`
- [ ] `AgentStatusPayload` implemented:
  - `agent_id: str` — required
  - `state: Literal["running", "idle", "awaiting_approval", "error", "paused"]` — required
  - `task_id: str | None` — default `None`
  - `task_description: str | None` — default `None`
  - `error_message: str | None` — default `None`
- [ ] `ApprovalRequestPayload` implemented:
  - `request_id: str` — required
  - `agent_id: str` — required
  - `action_description: str` — required
  - `risk_level: Literal["low", "medium", "high"]` — required
  - `details: dict[str, Any]` — required
  - `timeout_seconds: int` — default `300`
- [ ] `ApprovalResponsePayload` implemented:
  - `request_id: str` — required
  - `decision: Literal["approve", "reject", "defer", "override"]` — required
  - `decided_by: str` — required
  - `notes: str | None` — default `None`
- [ ] `CommandPayload` implemented:
  - `command: str` — required
  - `args: dict[str, Any]` — default `{}`
  - `correlation_id: str | None` — default `None`
- [ ] `ResultPayload` implemented:
  - `command: str` — required
  - `result: dict[str, Any]` — required
  - `correlation_id: str | None` — default `None`
  - `success: bool` — required
- [ ] All models use `ConfigDict(extra="ignore")` (ADR-002)
- [ ] All fields have `Field(description=...)` annotations
- [ ] All classes exported in `src/nats_core/events/__init__.py`
- [ ] All modified files pass project-configured lint/format checks with zero errors
- [ ] `mypy src/` passes with zero errors

## Implementation Notes

- Reference: `docs/design/contracts/API-message-contracts.md`
- `Literal` constraints are enforced by Pydantic v2 at parse time — no custom validator needed
- `details` field in `ApprovalRequestPayload` may use `dict[str, Any]` — acceptable for extensible metadata
- `_agent.py` is a private module; public names re-exported from `events/__init__.py`
- Do NOT implement tests — that is TASK-ETS5
