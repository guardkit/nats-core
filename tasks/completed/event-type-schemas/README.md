# Feature: Event Type Schemas (FEAT-ETS)

Typed payload schemas for every event in the nats-core system.

## Summary

| | |
|---|---|
| **Feature ID** | FEAT-ETS |
| **Review Task** | TASK-ETS0 |
| **Complexity** | 5/10 (Medium) |
| **Tasks** | 5 (4 parallel + 1 sequential) |
| **BDD Scenarios** | 46 (10 smoke, 14 boundary, 8 negative, 14 edge-case) |

## Prerequisites

- TASK-ME01 (project scaffolding) — must be complete
- TASK-ME02 (EventType enum + MessageEnvelope) — must be complete

## Tasks

| Task | Description | Wave | Mode | Complexity |
|------|-------------|------|------|-----------|
| [TASK-ETS1](TASK-ETS1-pipeline-event-payloads.md) | Pipeline event payloads (6 classes) | 1 | task-work | 5 |
| [TASK-ETS2](TASK-ETS2-agent-event-payloads.md) | Agent event payloads (5 classes) | 1 | task-work | 3 |
| [TASK-ETS3](TASK-ETS3-jarvis-event-payloads.md) | Jarvis event payloads (4 classes) | 1 | task-work | 3 |
| [TASK-ETS4](TASK-ETS4-fleet-event-payloads.md) | Fleet payloads + AgentManifest (5 classes) | 1 | task-work | 5 |
| [TASK-ETS5](TASK-ETS5-dispatcher-and-tests.md) | Dispatcher complete + 46 BDD tests | 2 | task-work | 5 |

## Execution

```bash
# Wave 1 — run in parallel (no cross-domain deps)
/task-work TASK-ETS1  # or run concurrently:
/task-work TASK-ETS2
/task-work TASK-ETS3
/task-work TASK-ETS4

# Wave 2 — after all Wave 1 tasks complete
/task-work TASK-ETS5
```

## Feature Spec

- `features/event-type-schemas/event-type-schemas.feature`
- `features/event-type-schemas/event-type-schemas_summary.md`

## Design References

- `docs/design/contracts/API-message-contracts.md`
- `docs/design/models/DM-message-contracts.md`
- `docs/design/contracts/API-fleet-registration.md`
- `docs/design/models/DM-fleet-registration.md`
- `docs/design/decisions/ADR-002-schema-versioning.md`
- `docs/design/decisions/DDR-002-publish-full-manifest.md`
