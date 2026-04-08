---
id: TASK-ME02
title: "Implement EventType enum and MessageEnvelope model"
status: pending
task_type: declarative
parent_review: TASK-40B8
feature_id: FEAT-ME
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
  - TASK-ME01
priority: high
tags: [pydantic, model, envelope]
---

# Task: Implement EventType enum and MessageEnvelope model

## Description

Implement the `EventType` enum and `MessageEnvelope` Pydantic model in `src/nats_core/envelope.py`.
These form the wire format for all NATS messages in the fleet. Follow the data model spec
(DM-message-contracts.md) and API contract (API-message-contracts.md) exactly.

## Acceptance Criteria

- [ ] `EventType` enum implemented as `str, Enum` subclass with all 16 values across 4 domains:
  - Pipeline: FEATURE_PLANNED, FEATURE_READY_FOR_BUILD, BUILD_STARTED, BUILD_PROGRESS, BUILD_COMPLETE, BUILD_FAILED
  - Agent: STATUS, APPROVAL_REQUEST, APPROVAL_RESPONSE, COMMAND, RESULT, ERROR
  - Jarvis: INTENT_CLASSIFIED, DISPATCH, AGENT_RESULT, NOTIFICATION
  - Fleet: AGENT_REGISTER, AGENT_HEARTBEAT, AGENT_DEREGISTER
- [ ] `MessageEnvelope` Pydantic BaseModel implemented with fields:
  - `message_id: str` — default_factory = `lambda: str(uuid4())`
  - `timestamp: datetime` — default_factory = UTC now
  - `version: str` — default = "1.0"
  - `source_id: str` — required, min_length=1
  - `event_type: EventType` — required
  - `project: str | None` — default = None
  - `correlation_id: str | None` — default = None
  - `payload: dict[str, Any]` — required
- [ ] `model_config = ConfigDict(extra="ignore")` set for forward compatibility (ADR-002)
- [ ] All fields have `Field(description=...)` annotations
- [ ] JSON serialisation uses ISO 8601 for timestamps
- [ ] `payload_class_for_event_type()` helper function stubbed (returns NotImplementedError for now)
- [ ] Public API re-exported from `src/nats_core/__init__.py`
- [ ] `from __future__ import annotations` at top of module
- [ ] Google-style docstrings on all public API
- [ ] All modified files pass project-configured lint/format checks with zero errors
- [ ] `mypy src/` passes with zero errors

## Implementation Notes

- Reference: `docs/design/models/DM-message-contracts.md` for field specifications
- Reference: `docs/design/contracts/API-message-contracts.md` for public API surface
- Reference: `docs/design/decisions/ADR-002-schema-versioning.md` for extra="ignore" rationale
- Use `Field(description=...)` on every field per project patterns
- Use `default_factory` for mutable defaults (uuid, datetime)
- Keep model as pure data container — no I/O
- `payload_class_for_event_type()` will be fully implemented when event payload models are added
