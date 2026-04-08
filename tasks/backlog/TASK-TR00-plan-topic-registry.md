---
id: TASK-TR00
title: "Plan: Topic Registry"
status: completed
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
priority: high
task_type: review
tags: [topic-registry, planning, nats-subjects]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: Topic Registry

## Description

Review and plan the implementation of the Topic Registry — typed string constants for all NATS subjects across five namespaces (Pipeline, Agents, Fleet, Jarvis, System) with template resolution via `Topics.resolve()` and multi-tenancy project scoping via `Topics.for_project()`. Covers identifier validation, wildcard topic correctness, and synchronisation between topic templates and the EventType enum.

## Context

- Feature spec: `features/topic-registry/topic-registry.feature` (32 BDD scenarios)
- API contract: `docs/design/contracts/API-topic-registry.md`
- System spec: `docs/design/specs/nats-core-system-spec.md`
- Depends on: Feature 2 (Event Type Schemas) — EventType enum
- Target module: `src/nats_core/topics.py`

## Review Focus

- All aspects (comprehensive analysis)
- Trade-off priority: Balanced

## Acceptance Criteria

- [x] Technical options analysed for Topics class implementation
- [x] Architecture implications assessed (nested classes, validation approach)
- [x] Effort estimation and complexity assessment completed
- [x] Risk analysis and potential blockers identified
- [x] Implementation breakdown with subtasks recommended
