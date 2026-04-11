# Feature: Message Envelope

**Feature ID**: FEAT-ME
**Status**: Planned
**Complexity**: 4/10
**Estimated Effort**: ~2.5 hours

## Problem Statement

The nats-core library needs a base `MessageEnvelope` Pydantic schema that serves as the
wire format for all NATS messages in the fleet. Every agent, adapter, and service depends
on this schema. It must support construction with sensible defaults, JSON round-tripping,
forward-compatible parsing, correlation ID propagation, and multi-tenant project scoping.

## Solution Approach

Scaffold-first approach: create the project structure (pyproject.toml, src layout, tooling)
in Wave 1, then implement the MessageEnvelope model and its 23-scenario test suite in Wave 2.

This separation ensures:
- Clean scaffolding gets correct quality gate profile (no arch review needed)
- Model implementation gets proper declarative quality gates
- Test suite is independently verifiable against BDD specifications

## Tasks

| # | Task | Type | Complexity | Wave |
|---|------|------|-----------|------|
| 1 | [TASK-ME01](TASK-ME01-project-scaffolding.md) — Project scaffolding | scaffolding | 3 | 1 |
| 2 | [TASK-ME02](TASK-ME02-message-envelope-model.md) — EventType + MessageEnvelope model | declarative | 4 | 2 |
| 3 | [TASK-ME03](TASK-ME03-message-envelope-tests.md) — Test suite (23 BDD scenarios) | testing | 4 | 2 |

## Context Documents

- [System Spec](../../../docs/design/specs/nats-core-system-spec.md)
- [Data Model](../../../docs/design/models/DM-message-contracts.md)
- [API Contract](../../../docs/design/contracts/API-message-contracts.md)
- [Schema Versioning ADR](../../../docs/design/decisions/ADR-002-schema-versioning.md)
- [BDD Scenarios](../../../features/message-envelope/message-envelope.feature) (23 scenarios)

## Next Steps

```bash
# Start with Wave 1
/task-work TASK-ME01

# After Wave 1 completes, run Wave 2
/task-work TASK-ME02
/task-work TASK-ME03
```
