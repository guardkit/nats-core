# Fleet Registration — Implementation Guide

**Feature ID:** FEAT-FR01
**Parent review:** TASK-B5F3
**Tasks:** 6 (5 waves)
**Approach:** Sequential waves with max in-wave parallelism
**Execution:** Auto-detect (Wave 4 eligible for parallel)
**Testing:** Standard (BDD-driven, `InMemoryManifestRegistry` for unit tests)

---

## Data Flow: Read/Write Paths

```mermaid
flowchart LR
    subgraph Writes["Write Paths"]
        W1["AgentManifest published\nto fleet.register"]
        W2["AgentHeartbeatPayload\nto fleet.heartbeat.{agent_id}"]
        W3["AgentDeregistrationPayload\nto fleet.deregister"]
    end

    subgraph Storage["Storage"]
        S1[("agent-registry KV\nNATSKVManifestRegistry")]
        S2[("HeartbeatRecord dict\nin-process liveness state")]
    end

    subgraph Reads["Read Paths"]
        R1["select_agent()\nconfidence + queue-depth routing"]
        R2["check_timeouts()\nliveness detection"]
        R3["list_all() / find_by_intent()\nrouter queries registry"]
    end

    W1 -->|"register(manifest)"| S1
    W2 -->|"record_heartbeat()"| S2
    W3 -->|"deregister(agent_id)"| S1

    S1 -->|"list_all() / find_by_intent()"| R1
    S2 -->|"heartbeats dict"| R1
    S2 -->|"heartbeats dict"| R2
    S1 -->|"list_all()"| R3

    style R1 fill:#cfc,stroke:#090
    style R2 fill:#cfc,stroke:#090
    style R3 fill:#cfc,stroke:#090
```

_All write paths have corresponding read paths. No disconnected paths._

---

## Integration Contracts

```mermaid
sequenceDiagram
    participant Agent as Fleet Agent
    participant Registry as NATSKVManifestRegistry
    participant KV as NATS KV Bucket
    participant Router as Router / Dispatcher
    participant Routing as _routing.select_agent()

    Agent->>Registry: register(AgentManifest)
    Registry->>KV: kv.put(agent_id, json_bytes)
    KV-->>Registry: ok

    Agent->>Registry: heartbeat received
    Note over Registry: record_heartbeat() updates HeartbeatRecord

    Router->>Registry: list_all()
    Registry->>KV: keys() + get() per key
    KV-->>Registry: AgentManifest entries
    Registry-->>Router: list[AgentManifest]

    Router->>Routing: select_agent(candidates, intent, heartbeats)
    Note over Routing: confidence sort → queue-depth tiebreak → capacity gate
    Routing-->>Router: AgentManifest | None

    Agent->>Registry: deregister(agent_id)
    Registry->>KV: kv.delete(agent_id)
```

_Data passes from KV → Registry → Router → Routing at every dispatch. No fetch-then-discard._

---

## Task Dependencies

```mermaid
graph TD
    T1[TASK-FR-001\nScaffolding] --> T2[TASK-FR-002\nPydantic Models]
    T2 --> T3[TASK-FR-003\nManifestRegistry ABC\n+ InMemory]
    T3 --> T4[TASK-FR-004\nNATSKVManifestRegistry]
    T3 --> T5[TASK-FR-005\nHeartbeat Monitor\n+ Routing Logic]
    T4 --> T6[TASK-FR-006\nTest Suite]
    T5 --> T6

    style T4 fill:#cfc,stroke:#090
    style T5 fill:#cfc,stroke:#090
```

_TASK-FR-004 and TASK-FR-005 (green) can run in parallel in Wave 4 — no file conflicts._

---

## §4: Integration Contracts

Cross-task data dependencies that must be satisfied at integration boundaries.

### Contract: AgentManifest

- **Producer task:** TASK-FR-002
- **Consumer task(s):** TASK-FR-003, TASK-FR-006
- **Artifact type:** Python Pydantic model
- **Format constraint:** `from nats_core.manifest import AgentManifest` — the registry stores and retrieves instances of this model. Fields `agent_id`, `name`, `template` are required; `intents` must be non-empty at registration time.
- **Validation method:** Coach verifies `AgentManifest` is importable from `nats_core.manifest` and that `InMemoryManifestRegistry.register()` accepts it without error.

### Contract: ManifestRegistry ABC

- **Producer task:** TASK-FR-003
- **Consumer task(s):** TASK-FR-004, TASK-FR-005, TASK-FR-006
- **Artifact type:** Python Abstract Base Class
- **Format constraint:** `from nats_core.manifest import ManifestRegistry` — `NATSKVManifestRegistry` must subclass this ABC and implement all abstract methods: `register`, `deregister`, `get`, `list_all`, `find_by_intent`, `find_by_tool`. The routing functions in `_routing.py` receive a `ManifestRegistry` instance and call `list_all()` and `find_by_intent()`.
- **Validation method:** Coach verifies `issubclass(NATSKVManifestRegistry, ManifestRegistry)` is `True` and `mypy --strict` passes.

---

## Execution Strategy

### Wave 1 — Scaffolding (sequential)
- **TASK-FR-001**: Create `manifest.py`, `_routing.py`, `events/fleet.py` stubs, `py.typed`
- Duration: ~15 min

### Wave 2 — Models (sequential)
- **TASK-FR-002**: All Pydantic models with validators
- Duration: ~60 min

### Wave 3 — Registry Interface (sequential)
- **TASK-FR-003**: `ManifestRegistry` ABC + `InMemoryManifestRegistry`
- Duration: ~45 min

### Wave 4 — KV Registry + Routing (parallel)
- **TASK-FR-004**: `NATSKVManifestRegistry` in `client.py` (no overlap with `_routing.py`)
- **TASK-FR-005**: `select_agent`, `record_heartbeat`, `check_timeouts` in `_routing.py`
- Files are disjoint — safe to run in parallel
- Duration: ~90 min each

### Wave 5 — Test Suite (sequential)
- **TASK-FR-006**: All 28 BDD scenarios across 4 test files + conftest.py
- Duration: ~90 min

---

## Architecture Notes

### Module Placement

| Module | Path | Rationale |
|--------|------|-----------|
| Pydantic models | `src/nats_core/manifest.py` | Same file as ManifestRegistry — single import surface |
| Registry ABC + InMemory | `src/nats_core/manifest.py` | InMemory is a first-class impl, not test infra |
| NATS KV registry | `src/nats_core/client.py` | Consistent with NATSClient placement (both need nats-py) |
| Routing logic | `src/nats_core/_routing.py` | Private module — pure functions, no I/O |
| Fleet event payloads | `src/nats_core/events/fleet.py` | Domain-grouped with other event schemas |

### Key Design Decisions

1. **`ManifestRegistry` ABC enables `InMemoryManifestRegistry` as first-class impl** — not just a test double. Consumers running without NATS (e.g. local dev, unit tests) use it directly.

2. **Routing is pure** — `select_agent()` takes `candidates: list[AgentManifest]` and `heartbeats: dict[str, HeartbeatRecord]`. The caller queries the registry and passes results in. No async I/O inside routing.

3. **`time.monotonic()` for heartbeat timeouts** — avoids wall-clock drift and is safe under sleep/resume.

4. **`model_dump_json().encode()` for KV storage** — deterministic JSON bytes. `model_validate_json()` for deserialization.

5. **`extra="ignore"` on `AgentManifest`** — forward compatibility per ADR-002. Unknown fields in newer agent versions are silently dropped.

6. **Last-write-wins for concurrent registration** — NATS KV `put()` is atomic; the last writer wins. This is the documented behaviour per ADR-004 and the BDD `@concurrency` scenarios.

---

## Quality Gates

| Task | Type | Gate |
|------|------|------|
| TASK-FR-001 | scaffolding | File existence check; `python -c "import nats_core"` succeeds |
| TASK-FR-002 | declarative | mypy strict passes; Pydantic validators exercised |
| TASK-FR-003 | feature | `issubclass(InMemoryManifestRegistry, ManifestRegistry)`; seam test passes |
| TASK-FR-004 | feature | mypy strict; `issubclass(NATSKVManifestRegistry, ManifestRegistry)`; seam test passes |
| TASK-FR-005 | feature | mypy strict; routing unit tests pass; seam test passes |
| TASK-FR-006 | testing | All 28 tests pass; `pytest -m smoke` runs 3 tests; coverage >= 90% |
