---
id: TASK-NCFA-003
title: Add 4 pipeline-event payload types required by Forge orchestrator
status: completed
created: 2026-04-23T00:00:00Z
updated: 2026-04-23T00:00:00Z
completed: 2026-04-23T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/forge-v2-alignment/TASK-NCFA-003/
organized_files: ["TASK-NCFA-003.md"]
task_type: implementation
feature_id: FEAT-NCFA
priority: high
tags: [nats-core, payloads, topics, forge-system-design, pipeline-events]
complexity: 4
wave: 3
implementation_mode: task-work
dependencies: []
sibling_tasks: [TASK-NCFA-001]
test_results:
  status: passed
  coverage: 98
  last_run: 2026-04-23T00:00:00Z
  unit_tests_passed: 761
  unit_tests_failed: 0
---

# Task: Add 4 pipeline-event payload types required by Forge orchestrator

## Context

Forge's `/system-design` session (2026-04-23) produced an API contract
(`forge/docs/design/contracts/API-nats-pipeline-events.md`) that requires four
pipeline-event payload types that nats-core does not yet expose. Two were already
referenced by the Forge pipeline-orchestrator refresh doc (`StageCompletePayload`,
`BuildPausedPayload`); two are additive refinements Forge needs for clean downstream
filtering (`BuildResumedPayload`, `BuildCancelledPayload`).

Note: `StageCompletePayload` and `BuildPausedPayload` were added by TASK-NCFA-001
as part of the forge-v2.2 wave, but with a different field signature. This task
supersedes those definitions with the canonical field sets specified in the Forge
`/system-design` API contract — the two tasks should be reconciled during
implementation review. `BuildResumedPayload` and `BuildCancelledPayload` are net-new
additions not covered by TASK-NCFA-001.

Until this task ships, Forge carries these four payloads locally in
`forge/forge/adapters/nats/_interim_payloads.py` with a TODO pointing here. That
interim module will be deleted once Forge bumps its `nats-core` dependency pin to
`>= 0.2.0`.

The full dependency decision is recorded in
`forge/docs/design/decisions/DDR-001-reply-subject-correlation.md`.

## Authoritative specs

- **Forge API contract:** `forge/docs/design/contracts/API-nats-pipeline-events.md` §3.2
- **Forge dependency decision:** `forge/docs/design/decisions/DDR-001-reply-subject-correlation.md`

## Scope

### 1. Add / reconcile payloads in `src/nats_core/events/_pipeline.py`

All four payloads use `ConfigDict(extra="allow")` for forward compatibility
(consistent with the forward-compat decision from TASK-7448). Every payload carries
`correlation_id: str` as a required field.

#### `StageCompletePayload`

Reconcile with the version added in TASK-NCFA-001. The canonical field set
per the Forge API contract:

```python
class StageCompletePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    feature_id: str
    build_id: str
    stage_label: str
    target_kind: Literal["local_tool", "fleet_capability", "subagent"]
    target_identifier: str
    status: Literal["PASSED", "FAILED", "GATED", "SKIPPED"]
    gate_mode: Literal[
        "AUTO_APPROVE", "FLAG_FOR_REVIEW", "HARD_STOP", "MANDATORY_HUMAN_APPROVAL"
    ] | None
    coach_score: float | None
    duration_secs: float
    completed_at: str  # ISO 8601
    correlation_id: str
```

#### `BuildPausedPayload`

Reconcile with the version added in TASK-NCFA-001. The canonical field set:

```python
class BuildPausedPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    feature_id: str
    build_id: str
    stage_label: str
    gate_mode: Literal[
        "FLAG_FOR_REVIEW", "HARD_STOP", "MANDATORY_HUMAN_APPROVAL"
    ]
    coach_score: float | None
    rationale: str
    approval_subject: str
    paused_at: str  # ISO 8601
    correlation_id: str
```

Note: `gate_mode` here is a subset of the full literal — `AUTO_APPROVE` is excluded
because a build only pauses when a gate requires human action.

#### `BuildResumedPayload` (net-new)

```python
class BuildResumedPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    feature_id: str
    build_id: str
    stage_label: str
    decision: Literal["approve", "reject", "defer", "override"]
    responder: str
    resumed_at: str  # ISO 8601
    correlation_id: str
```

Emitted after `ApprovalResponsePayload` rehydrates and the LangGraph graph resumes.

#### `BuildCancelledPayload` (net-new)

```python
class BuildCancelledPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    feature_id: str
    build_id: str
    reason: str
    cancelled_by: str
    cancelled_at: str  # ISO 8601
    correlation_id: str
```

Emitted when the running build sees a cancel command on the pipeline.

### 2. Add topic constants to `src/nats_core/topics.py`

`STAGE_COMPLETE` and `BUILD_PAUSED` were added by TASK-NCFA-001; confirm they match
the Forge contract and are already present. Add the two net-new entries to
`Topics.Pipeline`:

```python
BUILD_RESUMED   = "pipeline.build-resumed.{feature_id}"
BUILD_CANCELLED = "pipeline.build-cancelled.{feature_id}"
```

`BUILD_RESUMED` may already be present from TASK-NCFA-001 — confirm and skip if so.

### 3. Add `EventType` enum members in `src/nats_core/envelope.py`

Confirm or add:

```python
STAGE_COMPLETE  = "stage_complete"
BUILD_PAUSED    = "build_paused"
BUILD_RESUMED   = "build_resumed"
BUILD_CANCELLED = "build_cancelled"
```

`STAGE_COMPLETE`, `BUILD_PAUSED`, and `BUILD_RESUMED` were added by TASK-NCFA-001.
Only `BUILD_CANCELLED` is guaranteed net-new.

### 4. Register payloads in `_EVENT_TYPE_REGISTRY`

Confirm or add entries in `envelope.py`:

```python
EventType.STAGE_COMPLETE:  StageCompletePayload,
EventType.BUILD_PAUSED:    BuildPausedPayload,
EventType.BUILD_RESUMED:   BuildResumedPayload,
EventType.BUILD_CANCELLED: BuildCancelledPayload,
```

### 5. Export the symbols

Update `src/nats_core/events/__init__.py` so that:

```python
from nats_core.events.pipeline import (
    StageCompletePayload,
    BuildPausedPayload,
    BuildResumedPayload,
    BuildCancelledPayload,
)
```

works. Add all four to the import list and `__all__`. (Some may already be exported
from TASK-NCFA-001 — confirm and add only what is missing.)

### 6. Unit tests in `tests/test_events.py`

Add unit tests covering each new or reconciled payload. For each payload, add at
minimum:

- Field validation — required fields are enforced, missing fields raise `ValidationError`
- Serde round-trip — `model.model_dump()` followed by `Payload.model_validate(...)` returns an equal instance
- Literal rejection — invalid literal values raise `ValidationError`
- Forward-compat — extra fields are accepted without error (`ConfigDict(extra="allow")`)

Suggested test names:

- `test_stage_complete_payload_validates_required_fields`
- `test_stage_complete_payload_rejects_invalid_status_literal`
- `test_stage_complete_payload_rejects_invalid_target_kind`
- `test_stage_complete_payload_accepts_null_gate_mode_and_coach_score`
- `test_stage_complete_payload_serde_round_trip`
- `test_build_paused_payload_validates_required_fields`
- `test_build_paused_payload_rejects_auto_approve_gate_mode`
- `test_build_paused_payload_serde_round_trip`
- `test_build_resumed_payload_validates_required_fields`
- `test_build_resumed_payload_rejects_invalid_decision_literal`
- `test_build_resumed_payload_serde_round_trip`
- `test_build_cancelled_payload_validates_required_fields`
- `test_build_cancelled_payload_serde_round_trip`
- `test_all_four_payloads_accept_extra_fields` (forward-compat for all four)

### 7. Bump version to 0.2.0

In `pyproject.toml`, bump the `version` field from its current value to `0.2.0`.
These additions are additive (no breaking changes) but warrant a minor bump per
semver given they add a net-new public API surface.

## Acceptance criteria

- [ ] `from nats_core.events.pipeline import StageCompletePayload, BuildPausedPayload, BuildResumedPayload, BuildCancelledPayload` works without error
- [ ] Each payload validates required fields and raises `ValidationError` on malformed inputs (tested)
- [ ] `Topics.Pipeline.STAGE_COMPLETE`, `Topics.Pipeline.BUILD_PAUSED`, `Topics.Pipeline.BUILD_RESUMED`, `Topics.Pipeline.BUILD_CANCELLED` all resolve via `Topics.resolve(..., feature_id="FEAT-XXX")`
- [ ] `EventType.STAGE_COMPLETE`, `EventType.BUILD_PAUSED`, `EventType.BUILD_RESUMED`, `EventType.BUILD_CANCELLED` present in enum
- [ ] `_EVENT_TYPE_REGISTRY` maps all four `EventType` values to their payload classes
- [ ] `BuildPausedPayload` rejects `gate_mode="AUTO_APPROVE"` (that value is excluded from its literal)
- [ ] All four payloads accept unknown extra fields without error
- [ ] All four payloads serde round-trip cleanly
- [ ] Existing callers are not broken — `EventType` additions are additive, no existing member removed
- [ ] `pyproject.toml` version is `0.2.0`
- [ ] `pytest --cov` reports >= 98% coverage (matching existing baseline)
- [ ] No existing tests broken

## Out of scope

- Integration tests against live NATS (separate follow-up if needed, per TASK-NCFA-002 precedent)
- Deleting `FeaturePlannedPayload` or `FeatureReadyForBuildPayload` (retirement is TASK-NCFA-001 scope)
- Any `MessageEnvelope` or `NATSClient` changes
- Forge-side deletion of `forge/forge/adapters/nats/_interim_payloads.py` — that is a Forge task once this ships
- Any `jarvis.*` or `fleet.*` topic additions
- Load or stress testing

## Dependencies

- No upstream nats-core tasks block this — it is a pure library addition.
- Should ship alongside or immediately after TASK-NCFA-001's retirement items in the same `nats-core >= 0.2.0` release.

## Cross-repo references

- **Sibling task:** TASK-NCFA-001 (Feature*Payload retirement — should land in same release)
- **Forge dependency decision:** `forge/docs/design/decisions/DDR-001-reply-subject-correlation.md`
- **Forge API contract:** `forge/docs/design/contracts/API-nats-pipeline-events.md` §3.2
- **Forge interim payloads:** `forge/forge/adapters/nats/_interim_payloads.py` (deleted once this ships and Forge bumps pin)
