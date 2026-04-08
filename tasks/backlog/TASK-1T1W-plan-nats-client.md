---
id: TASK-1T1W
title: "Plan: NATS Client"
status: in_review
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
priority: high
task_type: review
tags: [nats-client, planning, pub-sub, fleet, typed-messaging]
complexity: 0
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: NATS Client

## Description

Review and plan the implementation of the typed publish/subscribe wrapper (`NATSClient`) around nats-py.
Covers automatic `MessageEnvelope` wrapping/unwrapping, topic resolution via the `Topics` registry,
project-scoped multi-tenancy, fleet registration convenience methods (register, deregister, heartbeat,
fleet registry read, fleet watch), and agent-to-agent tool invocation via request-reply.
Also covers connection lifecycle (connect, reconnect, graceful disconnect with drain) and
error handling for disconnected clients, malformed messages, and timeout scenarios.

## Context

- Feature spec: `features/nats-client/nats-client.feature` (33 BDD scenarios)
- Feature summary: `features/nats-client/nats-client_summary.md`
- API contract: `docs/design/contracts/API-nats-client.md`
- Data model: `docs/design/models/DM-nats-client.md`
- Fleet registration contract: `docs/design/contracts/API-fleet-registration.md`
- Topic registry contract: `docs/design/contracts/API-topic-registry.md`
- Component diagram: `docs/design/diagrams/nats-core-components.md`
- ADR-003: nats-py vs FastStream (nats-py selected)
- ADR-004: Dynamic Fleet Registration

## Review Focus

- All aspects (comprehensive analysis)
- Trade-off priority: Balanced (quality, maintainability, delivery speed)

## Acceptance Criteria

- [ ] Technical options analysed for NATSClient implementation
- [ ] Architecture implications assessed (module boundaries, async safety)
- [ ] Effort estimation and complexity assessment completed
- [ ] Risk analysis and potential blockers identified
- [ ] Implementation breakdown with subtasks recommended

## Implementation Notes

- `MessageEnvelope` feature (TASK-ME01-03) is already planned in backlog — NATSClient depends on it
- No `src/` or `pyproject.toml` exists yet — scaffolding task required if not already covered
- Must wrap nats-py only (ADR-003); no FastStream dependency
- Fleet convenience methods integrate with NATS KV JetStream bucket `agent-registry`
