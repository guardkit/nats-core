---
id: TASK-ETS3
title: Implement Jarvis event payload schemas
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
- jarvis
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-310F
  base_branch: main
  started_at: '2026-04-08T19:58:25.418554'
  last_updated: '2026-04-08T20:05:39.444519'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T19:58:25.418554'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/event-type-schemas/
---

# Task: Implement Jarvis event payload schemas

## Description

Implement the 4 Jarvis event payload classes in `src/nats_core/events/_jarvis.py`.
These cover Jarvis's intent classification and routing flow: intent classified →
dispatch → agent result → notification.

`IntentClassifiedPayload.confidence` must be constrained to 0.0–1.0 (same range as
`IntentCapability.confidence` in the fleet manifest).

## Acceptance Criteria

- [ ] `src/nats_core/events/_jarvis.py` created with `from __future__ import annotations`
- [ ] `IntentClassifiedPayload` implemented:
  - `input_text: str` — required (original user text)
  - `intent: str` — required (e.g., "software.build")
  - `confidence: float` — `ge=0.0, le=1.0`
  - `target_agent: str` — required (selected agent_id)
  - `correlation_id: str | None` — default `None`
- [ ] `DispatchPayload` implemented:
  - `intent: str` — required
  - `target_agent: str` — required
  - `input_text: str` — required
  - `correlation_id: str` — required
  - `context: dict[str, Any]` — default `{}`
- [ ] `AgentResultPayload` implemented:
  - `agent_id: str` — required
  - `intent: str` — required
  - `result: dict[str, Any]` — required
  - `correlation_id: str` — required
  - `success: bool` — required
- [ ] `NotificationPayload` implemented:
  - `message: str` — required
  - `level: Literal["info", "warning", "error"]` — default `"info"`
  - `adapter: str` — required (target adapter, e.g., "slack", "email")
  - `correlation_id: str | None` — default `None`
- [ ] All models use `ConfigDict(extra="ignore")` (ADR-002)
- [ ] All fields have `Field(description=...)` annotations
- [ ] All classes exported in `src/nats_core/events/__init__.py`
- [ ] All modified files pass project-configured lint/format checks with zero errors
- [ ] `mypy src/` passes with zero errors

## Implementation Notes

- Reference: `docs/design/contracts/API-message-contracts.md`
- `IntentClassifiedPayload.confidence` uses `Field(ge=0.0, le=1.0)` — same pattern as `IntentCapability.confidence` in manifest.py
- `_jarvis.py` is a private module; public names re-exported from `events/__init__.py`
- Do NOT implement tests — that is TASK-ETS5
