---
complexity: 5
consumer_context:
- consumes: PIPELINE_PAYLOAD_CLASSES
  driver: nats_core.events._pipeline
  format_note: All pipeline payload classes must be importable from nats_core.events
    and registered against their EventType enum member
  framework: Pydantic BaseModel (payload_class_for_event_type registry)
  task: TASK-ETS1
- consumes: AGENT_PAYLOAD_CLASSES
  driver: nats_core.events._agent
  format_note: All agent payload classes must be importable from nats_core.events
    and registered against their EventType enum member
  framework: Pydantic BaseModel (payload_class_for_event_type registry)
  task: TASK-ETS2
- consumes: JARVIS_PAYLOAD_CLASSES
  driver: nats_core.events._jarvis
  format_note: All Jarvis payload classes must be importable from nats_core.events
    and registered against their EventType enum member
  framework: Pydantic BaseModel (payload_class_for_event_type registry)
  task: TASK-ETS3
- consumes: FLEET_PAYLOAD_CLASSES
  driver: nats_core.events._fleet, nats_core.manifest
  format_note: AgentManifest registered for EventType.AGENT_REGISTER; AgentHeartbeatPayload
    and AgentDeregistrationPayload registered for their respective EventType members
  framework: Pydantic BaseModel + AgentManifest (payload_class_for_event_type registry)
  task: TASK-ETS4
dependencies:
- TASK-ETS1
- TASK-ETS2
- TASK-ETS3
- TASK-ETS4
feature_id: FEAT-ETS
id: TASK-ETS5
implementation_mode: task-work
parent_review: TASK-ETS0
priority: high
status: design_approved
tags:
- dispatcher
- tests
- pytest
- coverage
task_type: feature
title: Complete payload dispatcher and implement full test suite
wave: 2
---

# Task: Complete payload dispatcher and implement full test suite

## Description

Complete the `payload_class_for_event_type()` dispatcher in `src/nats_core/envelope.py`
(stubbed in TASK-ME02) and implement the full test suite covering all 46 BDD scenarios
from `features/event-type-schemas/event-type-schemas.feature`.

This is the integration and quality gate task for Feature 2 — it validates that all
domain payload tasks (TASK-ETS1–4) produced correctly typed, complete, and spec-compliant
schemas.

## Acceptance Criteria

### Dispatcher (`src/nats_core/envelope.py`)

- [ ] `payload_class_for_event_type()` fully implemented:
  - Returns the correct `type[BaseModel]` for every `EventType` member
  - Raises `KeyError` (not `NotImplementedError`) for unregistered types
  - Registry is a module-level `dict[EventType, type[BaseModel]]` constant
  - All 18 EventType members have a registered class
- [ ] `payload_class_for_event_type` re-exported from `src/nats_core/__init__.py`
- [ ] All modified files pass project-configured lint/format checks with zero errors
- [ ] `mypy src/` passes with zero errors

### Test Suite (`tests/test_event_type_schemas.py`)

**Key example scenarios (10 @smoke tests):**
- [ ] `EventType` enum contains all 18 documented event type strings
- [ ] Every `EventType` member has a registered payload class (via `payload_class_for_event_type`)
- [ ] `EventType.BUILD_STARTED` value equals `"build_started"` (str enum)
- [ ] `FeaturePlannedPayload` creates with feature_id, wave_count, task_count, waves
- [ ] `BuildProgressPayload` creates with wave, wave_total, overall_progress_pct
- [ ] `BuildCompletePayload` creates with tasks_completed/failed/total and optional pr_url
- [ ] `ApprovalRequestPayload` creates with risk_level "high", timeout_seconds defaults to 300
- [ ] `IntentClassifiedPayload` creates with confidence 0.92, target_agent
- [ ] `AgentManifest` creates with agent_id "product-owner-agent", intents list
- [ ] `DispatchPayload` creates with target_agent, intent, correlation_id

**Boundary scenarios (14 @boundary tests):**
- [ ] `build_id` matches pattern `build-{feature_id}-{YYYYMMDDHHMMSS}` (regex check)
- [ ] `overall_progress_pct` valid at 0.0, 50.0, 100.0
- [ ] `overall_progress_pct` rejects 100.1 (ValidationError)
- [ ] `overall_progress_pct` rejects -0.1 (ValidationError)
- [ ] `IntentCapability.confidence` valid at 0.0, 0.5, 1.0
- [ ] `IntentCapability.confidence` rejects 1.01 (ValidationError)
- [ ] `IntentCapability.confidence` rejects -0.01 (ValidationError)
- [ ] `IntentClassifiedPayload.confidence` rejects 1.5 (ValidationError)
- [ ] `AgentStatusPayload` accepts state in {"running","idle","awaiting_approval","error","paused"}
- [ ] `ApprovalRequestPayload` accepts risk_level in {"low","medium","high"}
- [ ] `ApprovalResponsePayload` accepts decision in {"approve","reject","defer","override"}
- [ ] `AgentHeartbeatPayload` accepts status in {"ready","busy","degraded","draining"}
- [ ] `AgentManifest` accepts status in {"ready","starting","degraded"}
- [ ] `AgentManifest` rejects max_concurrent=0 (ValidationError, ge=1)

**Negative scenarios (8 @negative tests):**
- [ ] `AgentStatusPayload` rejects state "sleeping" (ValidationError)
- [ ] `ApprovalRequestPayload` rejects risk_level "critical" (ValidationError)
- [ ] `ApprovalResponsePayload` rejects decision "ignore" (ValidationError)
- [ ] `AgentHeartbeatPayload` rejects status "offline" (ValidationError)
- [ ] `FeaturePlannedPayload` requires feature_id (ValidationError on omission)
- [ ] `BuildCompletePayload` requires build_id (ValidationError on omission)
- [ ] `AgentManifest` requires agent_id (ValidationError on omission)
- [ ] `DispatchPayload` requires target_agent (ValidationError on omission)

**Edge case scenarios (14 @edge-case tests):**
- [ ] No payload class has an untyped `dict[str, Any]` as a top-level field
  (exception: `ApprovalRequestPayload.details` is acceptable per spec)
- [ ] JSON round-trip fidelity for all 12 payload classes (model_dump → model_validate)
- [ ] Default values: `timeout_seconds=300`, `max_concurrent=1`, `status="ready"`, `reason="shutdown"`
- [ ] `BuildFailedPayload` carries `recoverable` flag and `failure_reason`
- [ ] Nested model validation: invalid `WaveSummary` inside `FeaturePlannedPayload` raises
- [ ] `extra="ignore"`: unknown field on `BuildCompletePayload` silently discarded
- [ ] `IntentCapability` missing `pattern` raises ValidationError pointing to nested field
- [ ] `AgentHeartbeatPayload` rejects `queue_depth=-1`, `active_tasks=-1`
- [ ] `AgentStatusPayload` with 10001-char `task_description` is accepted (no max_length)
- [ ] `AgentManifest` rejects `agent_id="Invalid Agent ID!"` (kebab-case regex)
- [ ] `BuildProgressPayload` rejects `wave=5, wave_total=3` (wave > wave_total)
- [ ] Two `AgentManifest` payloads with same `agent_id` are both individually valid
- [ ] `BuildCompletePayload` rejects `tasks_completed=8, tasks_failed=1, tasks_total=10` (8+1≠10)
- [ ] `FeaturePlannedPayload` rejects `wave_count=3` with only 2 `WaveSummary` entries

## Test Implementation Notes

- Use `conftest.py` factory function pattern (no pytest fixtures with mutable state)
- Group tests by scenario category using `@pytest.mark` tags matching BDD markers:
  - `@pytest.mark.smoke` — key examples
  - `@pytest.mark.boundary` — boundary conditions
  - `@pytest.mark.negative` — negative cases
  - `@pytest.mark.edge_case` — edge cases
- Use `pytest.raises(ValidationError)` for all negative/boundary rejection tests
- Reference: `features/event-type-schemas/event-type-schemas.feature` for exact scenario wording
- JSON round-trip test: `MyPayload.model_validate(payload.model_dump(mode="json"))`

## Seam Tests

The following seam tests validate the integration contracts with TASK-ETS1–4. Implement
these tests to verify the dispatcher registry boundary before full integration.

```python
"""Seam tests: verify payload class module contracts from TASK-ETS1-4."""
import pytest
from nats_core.envelope import EventType, payload_class_for_event_type


@pytest.mark.seam
@pytest.mark.integration_contract("PIPELINE_PAYLOAD_CLASSES")
def test_pipeline_payload_classes_registered():
    """Verify all pipeline EventType members are registered in the dispatcher.

    Contract: all pipeline payload classes must be importable from nats_core.events
    and registered against their EventType enum member.
    Producer: TASK-ETS1
    """
    pipeline_event_types = [
        EventType.FEATURE_PLANNED,
        EventType.FEATURE_READY_FOR_BUILD,
        EventType.BUILD_STARTED,
        EventType.BUILD_PROGRESS,
        EventType.BUILD_COMPLETE,
        EventType.BUILD_FAILED,
    ]
    for et in pipeline_event_types:
        cls = payload_class_for_event_type(et)
        assert cls is not None, f"No payload class registered for {et}"
        assert hasattr(cls, "model_fields"), f"{et}: registered class is not a Pydantic model"


@pytest.mark.seam
@pytest.mark.integration_contract("AGENT_PAYLOAD_CLASSES")
def test_agent_payload_classes_registered():
    """Verify all agent EventType members are registered in the dispatcher.

    Contract: all agent payload classes must be importable from nats_core.events
    and registered against their EventType enum member.
    Producer: TASK-ETS2
    """
    agent_event_types = [
        EventType.STATUS,
        EventType.APPROVAL_REQUEST,
        EventType.APPROVAL_RESPONSE,
        EventType.COMMAND,
        EventType.RESULT,
        EventType.ERROR,
    ]
    for et in agent_event_types:
        cls = payload_class_for_event_type(et)
        assert cls is not None, f"No payload class registered for {et}"
        assert hasattr(cls, "model_fields"), f"{et}: registered class is not a Pydantic model"


@pytest.mark.seam
@pytest.mark.integration_contract("JARVIS_PAYLOAD_CLASSES")
def test_jarvis_payload_classes_registered():
    """Verify all Jarvis EventType members are registered in the dispatcher.

    Contract: all Jarvis payload classes must be importable from nats_core.events
    and registered against their EventType enum member.
    Producer: TASK-ETS3
    """
    jarvis_event_types = [
        EventType.INTENT_CLASSIFIED,
        EventType.DISPATCH,
        EventType.AGENT_RESULT,
        EventType.NOTIFICATION,
    ]
    for et in jarvis_event_types:
        cls = payload_class_for_event_type(et)
        assert cls is not None, f"No payload class registered for {et}"
        assert hasattr(cls, "model_fields"), f"{et}: registered class is not a Pydantic model"


@pytest.mark.seam
@pytest.mark.integration_contract("FLEET_PAYLOAD_CLASSES")
def test_fleet_payload_classes_registered():
    """Verify all fleet EventType members are registered in the dispatcher.

    Contract: AgentManifest registered for AGENT_REGISTER; fleet payloads for heartbeat/deregister.
    Producer: TASK-ETS4
    """
    fleet_event_types = [
        EventType.AGENT_REGISTER,
        EventType.AGENT_HEARTBEAT,
        EventType.AGENT_DEREGISTER,
    ]
    for et in fleet_event_types:
        cls = payload_class_for_event_type(et)
        assert cls is not None, f"No payload class registered for {et}"
        assert hasattr(cls, "model_fields"), f"{et}: registered class is not a Pydantic model"
```