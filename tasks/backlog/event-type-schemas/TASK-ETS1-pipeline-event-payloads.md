---
id: TASK-ETS1
title: Implement pipeline event payload schemas
status: in_review
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
- pipeline
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-310F
  base_branch: main
  started_at: '2026-04-08T19:58:25.410247'
  last_updated: '2026-04-08T20:05:04.154643'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T19:58:25.410247'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement pipeline event payload schemas

## Description

Implement the 6 pipeline event payload classes and their nested models in
`src/nats_core/events/_pipeline.py`. These cover the full lifecycle of a feature
build: planned → ready → started → progress → complete/failed.

Cross-field validators are required for `BuildProgressPayload` (wave ≤ wave_total)
and `BuildCompletePayload` (tasks_completed + tasks_failed == tasks_total).

## Acceptance Criteria

- [ ] `src/nats_core/events/_pipeline.py` created with `from __future__ import annotations`
- [ ] `WaveSummary` Pydantic model implemented:
  - `wave_number: int` — `ge=1`
  - `task_count: int` — `ge=0`
  - `task_ids: list[str]` — list of task identifiers in this wave
- [ ] `TaskProgress` Pydantic model implemented:
  - `task_id: str` — required
  - `status: Literal["pending", "running", "complete", "failed"]`
  - `duration_seconds: int | None` — default `None`
- [ ] `FeaturePlannedPayload` implemented:
  - `feature_id: str` — required
  - `wave_count: int` — `ge=1`
  - `task_count: int` — `ge=1`
  - `waves: list[WaveSummary]` — required
  - Cross-field validator: `len(waves) == wave_count`
- [ ] `FeatureReadyForBuildPayload` implemented:
  - `feature_id: str` — required
  - `spec_path: str` — required
  - `plan_path: str` — required
  - `pipeline_type: Literal["greenfield", "existing"]` — required
  - `source_commands: list[str]` — default `[]`
- [ ] `BuildStartedPayload` implemented:
  - `feature_id: str` — required
  - `build_id: str` — required (format: `build-{feature_id}-{YYYYMMDDHHMMSS}`)
  - `wave_total: int` — `ge=1`
- [ ] `BuildProgressPayload` implemented:
  - `feature_id: str` — required
  - `build_id: str` — required
  - `wave: int` — `ge=1`
  - `wave_total: int` — `ge=1`
  - `overall_progress_pct: float` — `ge=0.0, le=100.0`
  - `elapsed_seconds: int` — `ge=0`
  - Cross-field validator: `wave <= wave_total`
- [ ] `BuildCompletePayload` implemented:
  - `feature_id: str` — required
  - `build_id: str` — required
  - `tasks_completed: int` — `ge=0`
  - `tasks_failed: int` — `ge=0`
  - `tasks_total: int` — `ge=1`
  - `pr_url: str | None` — default `None`
  - `duration_seconds: int` — `ge=0`
  - `summary: str` — required
  - Cross-field validator: `tasks_completed + tasks_failed == tasks_total`
- [ ] `BuildFailedPayload` implemented:
  - `feature_id: str` — required
  - `build_id: str` — required
  - `failure_reason: str` — required
  - `recoverable: bool` — required
  - `failed_task_id: str | None` — default `None`
- [ ] All models use `ConfigDict(extra="ignore")` (ADR-002)
- [ ] All fields have `Field(description=...)` annotations
- [ ] All classes exported in `src/nats_core/events/__init__.py`
- [ ] All modified files pass project-configured lint/format checks with zero errors
- [ ] `mypy src/` passes with zero errors

## Implementation Notes

- Reference: `docs/design/models/DM-message-contracts.md`
- Reference: `docs/design/decisions/ADR-002-schema-versioning.md`
- Use `@model_validator(mode="after")` for cross-field validation (Pydantic v2)
- Keep models as pure data containers — no I/O, no NATS references
- `_pipeline.py` is a private module; public names re-exported from `events/__init__.py`
- Do NOT implement tests — that is TASK-ETS5
