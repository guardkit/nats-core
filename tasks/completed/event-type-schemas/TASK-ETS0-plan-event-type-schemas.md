---
id: TASK-ETS0
title: "Plan: Event Type Schemas"
status: completed
task_type: review
priority: high
created: "2026-04-08T00:00:00Z"
clarification:
  context_a:
    timestamp: "2026-04-08T00:00:00Z"
    decisions:
      focus: all
      tradeoff: quality
      extensibility: yes
      concerns:
        - low_confidence_assumptions
        - cross_feature_dependencies
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/event-type-schemas/
---

# Plan: Event Type Schemas

## Feature Description

Typed payload schemas for every event in the system, covering pipeline events
(feature planned, build progress, build complete, build failed), agent events
(status, approval request/response), Jarvis events (intent classification, dispatch),
and fleet registration events (registration, heartbeat, deregistration).

The specification validates that all EventType enum members map to a corresponding
Pydantic payload class, enforces numeric bounds on progress and confidence fields,
constrains Literal-typed status and decision fields, and ensures JSON round-trip
fidelity across all payload types.

## Context

- Feature spec: `features/event-type-schemas/event-type-schemas.feature` (46 scenarios)
- Design contract: `docs/design/contracts/API-message-contracts.md`
- Data model: `docs/design/models/DM-message-contracts.md`
- ADR-002: Schema versioning (extra="ignore", optional-with-defaults for new fields)
- Depends on: TASK-ME02 (EventType enum + payload_class_for_event_type stub)

## Low-confidence Assumptions (require implementation decisions)

- ASSUM-007: No max_length constraint on string fields (behaviour undefined)
- ASSUM-008: agent_id must be kebab-case (pattern: ^[a-z][a-z0-9-]*$)
