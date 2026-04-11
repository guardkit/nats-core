---
id: TASK-ETS4
title: Implement fleet event payloads and agent manifest
status: completed
task_type: declarative
parent_review: TASK-ETS0
feature_id: FEAT-ETS
wave: 1
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-ME01
- TASK-ME02
priority: high
tags:
- pydantic
- events
- fleet
- manifest
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-310F
  base_branch: main
  started_at: '2026-04-08T19:58:25.414471'
  last_updated: '2026-04-08T20:06:17.803860'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T19:58:25.414471'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/event-type-schemas/
---

# Task: Implement fleet event payloads and agent manifest

## Description

Implement the fleet event payload classes and the `AgentManifest` capability declaration
in two modules:

- `src/nats_core/events/_fleet.py` — `AgentHeartbeatPayload`, `AgentDeregistrationPayload`
- `src/nats_core/manifest.py` — `IntentCapability`, `ToolCapability`, `AgentManifest`

`AgentManifest` is published directly to `fleet.register` and serves as the `agent_register`
event type payload (per DDR-002). The BDD spec tests it as "AgentRegistrationPayload" —
implement it as `AgentManifest` per the design contract.

The `agent_id` field on `AgentManifest` and `AgentDeregistrationPayload` must enforce
kebab-case format (ASSUM-008, confirmed low-confidence but spec has an explicit scenario).

## Acceptance Criteria

### `src/nats_core/manifest.py`

- [ ] `IntentCapability` implemented:
  - `pattern: str` — required, non-empty
  - `signals: list[str]` — default `[]`
  - `confidence: float` — `ge=0.0, le=1.0`
  - `description: str` — required
- [ ] `ToolCapability` implemented:
  - `name: str` — required, non-empty
  - `description: str` — required
  - `parameters: dict[str, Any]` — required (JSON Schema for input)
  - `returns: str` — required
  - `risk_level: Literal["read_only", "mutating", "destructive"]` — default `"read_only"`
  - `async_mode: bool` — default `False`
  - `requires_approval: bool` — default `False`
- [ ] `AgentManifest` implemented (maps to `EventType.AGENT_REGISTER`):
  - `agent_id: str` — required, `Field(pattern=r"^[a-z][a-z0-9-]*$", description="Kebab-case agent identifier")`
  - `name: str` — required
  - `version: str` — default `"0.1.0"`
  - `intents: list[IntentCapability]` — default `[]`
  - `tools: list[ToolCapability]` — default `[]`
  - `template: str` — required
  - `max_concurrent: int` — `ge=1`, default `1`
  - `status: Literal["ready", "starting", "degraded"]` — default `"ready"`
  - `trust_tier: Literal["core", "specialist", "extension"]` — default `"specialist"`
  - `required_permissions: list[str]` — default `[]`
  - `container_id: str | None` — default `None`
  - `metadata: dict[str, str]` — default `{}`
- [ ] `AgentManifest` uses `ConfigDict(extra="ignore")` (ADR-002)
- [ ] `AgentManifest`, `IntentCapability`, `ToolCapability` exported from `src/nats_core/__init__.py`

### `src/nats_core/events/_fleet.py`

- [ ] `AgentHeartbeatPayload` implemented:
  - `agent_id: str` — required
  - `status: Literal["ready", "busy", "degraded", "draining"]` — required
  - `queue_depth: int` — `ge=0`, default `0`
  - `active_tasks: int` — `ge=0`, default `0`
  - `uptime_seconds: int` — required, `ge=0`
  - `last_task_completed_at: datetime | None` — default `None`
  - `active_workflow_states: dict[str, str]` — default `{}`
- [ ] `AgentDeregistrationPayload` implemented:
  - `agent_id: str` — required, `Field(pattern=r"^[a-z][a-z0-9-]*$", description="Kebab-case agent identifier")`
  - `reason: str` — default `"shutdown"`
- [ ] Both fleet payloads use `ConfigDict(extra="ignore")` (ADR-002)
- [ ] Both fleet payloads exported in `src/nats_core/events/__init__.py`
- [ ] All modified files pass project-configured lint/format checks with zero errors
- [ ] `mypy src/` passes with zero errors

## Implementation Notes

- Reference: `docs/design/contracts/API-fleet-registration.md`
- Reference: `docs/design/models/DM-fleet-registration.md`
- Reference: `docs/design/decisions/DDR-002-publish-full-manifest.md`
- ASSUM-008 decision: enforce `^[a-z][a-z0-9-]*$` on `agent_id` — the BDD spec has
  an explicit scenario "Agent registration rejects invalid agent_id format"
- `AgentManifest` is NOT in `events/` — it lives in `manifest.py` alongside registry types
- BDD spec calls it "AgentRegistrationPayload"; implement as `AgentManifest` per DDR-002
- Do NOT implement tests — that is TASK-ETS5
