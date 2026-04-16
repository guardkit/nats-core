---
id: TASK-NCFA-001
title: Add BuildQueued / BuildPaused / BuildResumed / StageComplete / StageGated payloads and topics; deprecate FeaturePlanned
status: completed
completed: 2026-04-16
task_type: implementation
parent_review: forge/TASK-REV-A1F2
feature_id: FEAT-NCFA
priority: high
tags: [nats-core, payloads, topics, forge-v2.2, anchor]
complexity: 5
wave: 1
implementation_mode: task-work
dependencies: []
test_results:
  status: passed
  coverage: 98
  last_run: 2026-04-16
---

# Task: Add Forge v2.2 pipeline payloads and topics to nats-core

## Context

`forge/docs/research/forge-pipeline-architecture.md` v2.2 (post-TASK-REV-A1F2) specifies five pipeline payloads and five new topics that nats-core does not yet expose. The Forge build plan marks nats-core as "✅ implemented" but the audit in the alignment review §2.1 found it is missing every v2.2-critical pipeline payload. Without this task, Phase 2 of the anchor roadmap is blocked — there is no `BuildQueuedPayload` to publish, so nothing can trigger a build.

## Authoritative specs

- **`BuildQueuedPayload`:** full Pydantic model with validators, examples, and test list — `forge/docs/research/forge-build-plan-alignment-review.md` **Appendix C**
- **`BuildPausedPayload`, `BuildResumedPayload`, `StageCompletePayload`, `StageGatedPayload`:** sketches in anchor v2.2 §7, concrete field lists in this feature's `IMPLEMENTATION-GUIDE.md`
- **`agents.command.broadcast` topic:** plain string constant on `Topics.Agents`

## Scope

### 1. Add payloads to `src/nats_core/events/_pipeline.py`

- `BuildQueuedPayload` — copy verbatim from Appendix C including all field validators, `ConfigDict(extra='allow')`, and literal types
- `BuildPausedPayload` — per IMPLEMENTATION-GUIDE.md, with `ConfigDict(extra="allow")`
- `BuildResumedPayload` — per IMPLEMENTATION-GUIDE.md, with `ConfigDict(extra="allow")`
- `StageCompletePayload` — per IMPLEMENTATION-GUIDE.md, with `ConfigDict(extra="allow")` (note: there is no existing `StageComplete` — this is new)
- `StageGatedPayload` — per IMPLEMENTATION-GUIDE.md, with `ConfigDict(extra="allow")`

All five new payloads use `ConfigDict(extra="allow")` for forward compatibility — future publishers can add fields without breaking existing consumers. This is a deliberate v2.2 design decision, distinct from the existing payloads that use `extra="ignore"` per ADR-002.

Every new payload must carry `correlation_id: str` as a required field. Note: this is a domain-level correlation ID (threading build lifecycle events together), separate from the optional `correlation_id` on `MessageEnvelope` (infrastructure-level request-response linking).

### 2. Add topics to `src/nats_core/topics.py`

Append to `Topics.Pipeline`:

```python
BUILD_QUEUED  = "pipeline.build-queued.{feature_id}"
BUILD_PAUSED  = "pipeline.build-paused.{feature_id}"
BUILD_RESUMED = "pipeline.build-resumed.{feature_id}"
STAGE_COMPLETE = "pipeline.stage-complete.{feature_id}"
STAGE_GATED   = "pipeline.stage-gated.{feature_id}"
```

Append to `Topics.Agents`:

```python
COMMAND_BROADCAST = "agents.command.broadcast"
```

Do not rename existing entries. `COMMAND` / `RESULT` stay singular per ADR-SP-016.

### 3. Deprecate `FeaturePlannedPayload`

- Add `DeprecationWarning` on **instantiation** of `FeaturePlannedPayload` using Pydantic's `model_post_init`:
  ```python
  def model_post_init(self, __context: Any) -> None:
      import warnings
      warnings.warn(
          "FeaturePlannedPayload is deprecated; use BuildQueuedPayload",
          DeprecationWarning,
          stacklevel=2,
      )
  ```
  Do NOT use `__init_subclass__` (fires on subclassing, not instantiation) or module-level `warnings.warn` (fires on every `import nats_core` since `envelope.py` imports it at the top level).
- Update its docstring: `"""DEPRECATED: Use BuildQueuedPayload. Retained for backward compatibility, to be removed in nats-core v2.x."""`
- Mark `Topics.Pipeline.FEATURE_PLANNED` (`topics.py:79`) with a deprecation comment
- Update existing tests that instantiate `FeaturePlannedPayload` to use `pytest.warns(DeprecationWarning)`:
  - `tests/test_pipeline_payloads.py` — `TestFeaturePlannedPayload` class (~5 instantiations)
  - `tests/test_event_type_schemas.py` — factory function and direct instantiations (~6)
  - `tests/test_event_payloads_nc03.py` — factory function and direct instantiations (~3)

Do **not** delete — that is a semver-minor break. File a follow-up for removal.

### 4. Export the new symbols

Update `src/nats_core/events/__init__.py` so that `from nats_core.events import BuildQueuedPayload` etc. work. Add all five new payload classes to the import list and `__all__`.

### 5. Update EventType enum and payload registry

In `src/nats_core/envelope.py`:

- Add five new members to `EventType` enum:
  ```python
  BUILD_QUEUED = "build_queued"
  BUILD_PAUSED = "build_paused"
  BUILD_RESUMED = "build_resumed"
  STAGE_COMPLETE = "stage_complete"
  STAGE_GATED = "stage_gated"
  ```

- Add five new entries to `_EVENT_TYPE_REGISTRY`:
  ```python
  EventType.BUILD_QUEUED: BuildQueuedPayload,
  EventType.BUILD_PAUSED: BuildPausedPayload,
  EventType.BUILD_RESUMED: BuildResumedPayload,
  EventType.STAGE_COMPLETE: StageCompletePayload,
  EventType.STAGE_GATED: StageGatedPayload,
  ```

- Add the corresponding imports from `nats_core.events._pipeline`

Without these, `payload_class_for_event_type()` cannot dispatch the new event types.

### 6. Unit tests (TASK-NCFA-002 covers integration)

Add unit tests in `tests/events/test_pipeline.py`:

- `test_build_queued_payload_validates_feature_id_format` (FEAT-XXX regex)
- `test_build_queued_payload_validates_repo_format` (org/name regex)
- `test_build_queued_payload_adapter_required_for_jarvis`
- `test_build_queued_payload_cli_rejects_voice_adapter`
- `test_build_queued_payload_correlation_id_required`
- `test_build_queued_payload_forward_compat_extra_fields` (extra='allow')
- `test_build_paused_payload_requires_gate_mode`
- `test_build_resumed_payload_requires_decision`
- `test_stage_complete_payload_status_literal`
- `test_stage_gated_payload_requires_coach_score_and_threshold`
- `test_feature_planned_payload_emits_deprecation_warning` (use `pytest.warns(DeprecationWarning)`)

## Acceptance criteria

- [x] All five new payloads present in `_pipeline.py` with validators and `ConfigDict(extra="allow")`
- [x] All six new topic constants present (`Topics.Pipeline.BUILD_QUEUED`, etc. + `Topics.Agents.COMMAND_BROADCAST`)
- [x] Five new `EventType` enum members added to `envelope.py`
- [x] Five new entries added to `_EVENT_TYPE_REGISTRY` in `envelope.py`
- [x] `FeaturePlannedPayload` emits `DeprecationWarning` on instantiation (via `model_post_init`)
- [x] Existing tests updated with `pytest.warns(DeprecationWarning)` for `FeaturePlannedPayload`
- [x] Public API exports the new symbols via `events/__init__.py`
- [x] Unit tests listed above pass
- [x] `pytest --cov` reports ≥98% coverage (matching existing baseline)
- [x] No existing tests broken (singular `agents.command.*` convention preserved)
- [x] Grep for `agents.commands.` (plural) across the codebase returns 0 hits

## Out of scope

- Integration tests against live NATS on GB10 (TASK-NCFA-002)
- Deleting `FeaturePlannedPayload` — semver-minor follow-up
- Adding `jarvis.*` or `fleet.*` topics — those live in their own repos
- Any `MessageEnvelope` schema changes or `NATSClient` changes (note: `EventType` enum additions and `_EVENT_TYPE_REGISTRY` updates ARE in scope — these are registry additions, not schema changes)
- `FeatureReadyForBuildPayload` — decision pending TASK-FVD3 in forge repo; no action here
