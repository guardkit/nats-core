---
id: TASK-NC03
title: "Event payload models (events/ package)"
status: pending
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
priority: high
task_type: declarative
tags: [nats-client, events, pydantic, payload-models]
complexity: 3
wave: 2
implementation_mode: direct
parent_review: TASK-1T1W
feature_id: FEAT-1T1W
dependencies: [TASK-ME02]
consumer_context:
  - task: TASK-ME02
    consumes: MessageEnvelope
    framework: "Pydantic BaseModel (nats_core.envelope)"
    driver: "pydantic"
    format_note: "All payload models must be importable from nats_core.events.<domain>; they are carried in MessageEnvelope.payload and must be valid Pydantic BaseModel subclasses with ConfigDict(extra='ignore')"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Event payload models (events/ package)

## Description

Implement `src/nats_core/events/` package containing typed payload schemas for all
four domains: pipeline, agent, fleet, and jarvis. These are the models carried inside
`MessageEnvelope.payload`.

## Scope

### Package structure

```
src/nats_core/events/
    __init__.py       (re-exports all payload classes)
    pipeline.py
    agent.py
    fleet.py
    jarvis.py
```

### `events/pipeline.py`

| Class | Fields |
|-------|--------|
| `FeaturePlannedPayload` | `feature_id: str`, `title: str`, `description: str \| None = None` |
| `FeatureReadyForBuildPayload` | `feature_id: str`, `spec_path: str` |
| `BuildStartedPayload` | `feature_id: str`, `build_id: str`, `repo: str`, `branch: str` |
| `BuildProgressPayload` | `feature_id: str`, `build_id: str`, `tasks_completed: int`, `tasks_total: int`, `current_task: str \| None = None` |
| `BuildCompletePayload` | `feature_id: str`, `build_id: str`, `repo: str`, `branch: str`, `pr_url: str \| None = None`, `duration_seconds: float`, `tasks_completed: int`, `tasks_failed: int`, `tasks_total: int`, `summary: str` |
| `BuildFailedPayload` | `feature_id: str`, `build_id: str`, `error: str`, `failed_task: str \| None = None` |

### `events/agent.py`

| Class | Fields |
|-------|--------|
| `AgentStatusPayload` | `agent_id: str`, `state: Literal["ready","running","degraded","error","shutdown"]`, `message: str \| None = None` |
| `ApprovalRequestPayload` | `agent_id: str`, `task_id: str`, `description: str`, `options: list[str]` |
| `ApprovalResponsePayload` | `agent_id: str`, `task_id: str`, `approved: bool`, `choice: str \| None = None`, `reason: str \| None = None` |

### `events/fleet.py`

| Class | Fields |
|-------|--------|
| `AgentHeartbeatPayload` | `agent_id: str`, `status: Literal["healthy","degraded"]`, `queue_depth: int = 0`, `metadata: dict[str, str] = {}` |
| `AgentDeregistrationPayload` | `agent_id: str`, `reason: str = "shutdown"` |

### `events/jarvis.py`

| Class | Fields |
|-------|--------|
| `IntentClassifiedPayload` | `input_text: str`, `intent: str`, `confidence: float`, `adapter: str` |
| `DispatchPayload` | `agent_id: str`, `intent: str`, `input_text: str`, `correlation_id: str \| None = None` |

### `events/__init__.py`

Re-export all payload classes for convenience:

```python
from nats_core.events.pipeline import (
    FeaturePlannedPayload, FeatureReadyForBuildPayload,
    BuildStartedPayload, BuildProgressPayload,
    BuildCompletePayload, BuildFailedPayload,
)
from nats_core.events.agent import (
    AgentStatusPayload, ApprovalRequestPayload, ApprovalResponsePayload,
)
from nats_core.events.fleet import AgentHeartbeatPayload, AgentDeregistrationPayload
from nats_core.events.jarvis import IntentClassifiedPayload, DispatchPayload

__all__ = [...]
```

## Acceptance Criteria

- [ ] All 13 payload classes exist and instantiate with their required fields
- [ ] All models use `ConfigDict(extra="ignore")` for forward-compatible parsing
- [ ] All models use `from __future__ import annotations`
- [ ] All fields have `Field(description=...)`
- [ ] `BuildCompletePayload` serialises to JSON matching the wire format in `API-message-contracts.md`
- [ ] `AgentHeartbeatPayload` has mutable default factory for `metadata` (not `{}` directly)
- [ ] All payload classes importable from `nats_core.events` (top-level re-export)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

The following seam test validates the integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify MessageEnvelope contract from TASK-ME02."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("MessageEnvelope")
def test_message_envelope_carries_build_complete_payload():
    """Verify BuildCompletePayload is valid as MessageEnvelope.payload content.

    Contract: All payload models must be Pydantic BaseModel subclasses with
    ConfigDict(extra='ignore'), importable from nats_core.events.<domain>.
    Producer: TASK-ME02
    """
    from nats_core.events.pipeline import BuildCompletePayload

    payload = BuildCompletePayload(
        feature_id="FEAT-001",
        build_id="build-001",
        repo="appmilla/test",
        branch="main",
        duration_seconds=60.0,
        tasks_completed=3,
        tasks_failed=0,
        tasks_total=3,
        summary="All done",
    )

    data = payload.model_dump()
    assert data["feature_id"] == "FEAT-001"

    # Forward-compat: extra fields must be ignored
    payload2 = BuildCompletePayload.model_validate(
        {**data, "unknown_future_field": "ignored"}
    )
    assert payload2.feature_id == "FEAT-001"
```

## Implementation Notes

- All payload models are plain `BaseModel` (not `BaseSettings`)
- Use `default_factory=dict` for `metadata` in `AgentHeartbeatPayload`
- `Literal` types from `typing` (or `typing_extensions` for Python 3.10)

## Coach Validation Commands

```bash
python -c "from nats_core.events import BuildCompletePayload; print(BuildCompletePayload.__fields__.keys())"
python -c "from nats_core.events.fleet import AgentHeartbeatPayload; h = AgentHeartbeatPayload(agent_id='x'); print(h.metadata)"
ruff check src/nats_core/events/
mypy src/nats_core/events/
```
