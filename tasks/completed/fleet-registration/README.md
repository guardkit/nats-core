# Fleet Registration — Feature Tasks

**Feature:** FEAT-FR01
**Review:** TASK-B5F3
**Status:** Backlog

CAN bus-style dynamic agent discovery for nats-core. Agents self-announce on startup,
heartbeat every 30s, and are tracked in a NATS KV-backed routing table.

## Tasks

| Task | Title | Type | Complexity | Wave | Status |
|------|-------|------|-----------|------|--------|
| [TASK-FR-001](TASK-FR-001-fleet-registration-scaffolding.md) | Scaffolding | scaffolding | 2 | 1 | backlog |
| [TASK-FR-002](TASK-FR-002-fleet-registration-pydantic-models.md) | Pydantic models | declarative | 4 | 2 | backlog |
| [TASK-FR-003](TASK-FR-003-manifest-registry-abc-and-inmemory.md) | ManifestRegistry ABC + InMemory | feature | 4 | 3 | backlog |
| [TASK-FR-004](TASK-FR-004-nats-kv-manifest-registry.md) | NATSKVManifestRegistry | feature | 6 | 4 ‖ | backlog |
| [TASK-FR-005](TASK-FR-005-heartbeat-monitor-and-routing-logic.md) | Heartbeat monitor + routing | feature | 6 | 4 ‖ | backlog |
| [TASK-FR-006](TASK-FR-006-fleet-registration-test-suite.md) | Test suite (28 BDD scenarios) | testing | 4 | 5 | backlog |

_‖ = parallel execution eligible_

## Start Here

```bash
/task-work TASK-FR-001
```

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for full architecture notes,
data flow diagrams, integration contracts, and execution strategy.
