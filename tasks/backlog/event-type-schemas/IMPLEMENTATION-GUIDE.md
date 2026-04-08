# Implementation Guide: Event Type Schemas (FEAT-ETS)

**Feature:** Event Type Schemas
**Review Task:** TASK-ETS0
**Approach:** Domain-per-task (Option 1) — 4 parallel domain tasks, then dispatcher + tests

---

## Data Flow: Read/Write Paths

```mermaid
flowchart LR
    subgraph Writes["Write Paths (producers)"]
        W1["Pipeline Orchestrator\n.publish(FeaturePlannedPayload)"]
        W2["GuardKit Factory\n.publish(BuildProgressPayload)"]
        W3["Any Agent\n.publish(AgentStatusPayload)"]
        W4["Jarvis Router\n.publish(IntentClassifiedPayload)"]
        W5["Any Agent\n.publish(AgentManifest)"]
        W6["Any Agent\n.publish(AgentHeartbeatPayload)"]
    end

    subgraph Storage["NATS Subjects"]
        S1(["pipeline.feature-planned.*\npipeline.build-progress.*\netc."])
        S2(["agents.status.*\nagents.approval.*\netc."])
        S3(["jarvis.intent.classified\njarvis.dispatch.*\netc."])
        S4(["fleet.register\nfleet.heartbeat.*\nfleet.deregister"])
    end

    subgraph Reads["Read Paths (consumers)"]
        R1["MessageEnvelope.parse()\n→ payload_class_for_event_type()\n→ TypedPayload"]
        R2["Fleet Registry\n(AgentManifest subscriber)"]
        R3["Dashboard / Observers\n(build progress subscribers)"]
    end

    W1 -->|"wrap in MessageEnvelope"| S1
    W2 -->|"wrap in MessageEnvelope"| S1
    W3 -->|"wrap in MessageEnvelope"| S2
    W4 -->|"wrap in MessageEnvelope"| S3
    W5 -->|"wrap in MessageEnvelope"| S4
    W6 -->|"wrap in MessageEnvelope"| S4

    S1 -->|"via dispatcher"| R1
    S2 -->|"via dispatcher"| R1
    S3 -->|"via dispatcher"| R1
    S4 -->|"via registry sub"| R2
    S1 -->|"via observer sub"| R3

    style R1 fill:#cfc,stroke:#090
    style R2 fill:#cfc,stroke:#090
    style R3 fill:#cfc,stroke:#090
```

_All write paths wrap a typed payload in `MessageEnvelope`. All read paths decode via
`payload_class_for_event_type(envelope.event_type).model_validate(envelope.payload)`._

---

## Integration Contracts

```mermaid
sequenceDiagram
    participant ETS1 as TASK-ETS1<br/>(Pipeline Payloads)
    participant ETS2 as TASK-ETS2<br/>(Agent Payloads)
    participant ETS3 as TASK-ETS3<br/>(Jarvis Payloads)
    participant ETS4 as TASK-ETS4<br/>(Fleet Payloads)
    participant ETS5 as TASK-ETS5<br/>(Dispatcher + Tests)
    participant Envelope as envelope.py<br/>(payload_class_for_event_type)

    ETS1-->>ETS5: exports pipeline classes to events/__init__.py
    ETS2-->>ETS5: exports agent classes to events/__init__.py
    ETS3-->>ETS5: exports jarvis classes to events/__init__.py
    ETS4-->>ETS5: exports fleet classes to events/__init__.py<br/>+ AgentManifest to manifest.py

    ETS5->>Envelope: registers all 18 EventType → class mappings
    Note over ETS5,Envelope: REGISTRY: dict[EventType, type[BaseModel]]<br/>All 18 members must be present

    ETS5->>ETS5: runs 46 BDD scenario tests against<br/>all payload classes + dispatcher
```

_ETS1–4 run in parallel (Wave 1). ETS5 starts only after all Wave 1 tasks complete
(Wave 2). The dispatcher registry in `envelope.py` is the integration boundary._

---

## Task Dependencies

```mermaid
graph TD
    ME01["TASK-ME01<br/>Project Scaffolding<br/>(Feature 1)"]
    ME02["TASK-ME02<br/>EventType + MessageEnvelope<br/>(Feature 1)"]
    ETS1["TASK-ETS1<br/>Pipeline Payloads"]
    ETS2["TASK-ETS2<br/>Agent Payloads"]
    ETS3["TASK-ETS3<br/>Jarvis Payloads"]
    ETS4["TASK-ETS4<br/>Fleet Payloads + Manifest"]
    ETS5["TASK-ETS5<br/>Dispatcher + Tests"]

    ME01 --> ME02
    ME02 --> ETS1
    ME02 --> ETS2
    ME02 --> ETS3
    ME02 --> ETS4
    ETS1 --> ETS5
    ETS2 --> ETS5
    ETS3 --> ETS5
    ETS4 --> ETS5

    style ETS1 fill:#cfc,stroke:#090
    style ETS2 fill:#cfc,stroke:#090
    style ETS3 fill:#cfc,stroke:#090
    style ETS4 fill:#cfc,stroke:#090
    style ME01 fill:#eee,stroke:#999
    style ME02 fill:#eee,stroke:#999
```

_Green tasks (ETS1–4) can run in parallel. Grey tasks are Feature 1 prerequisites
that must complete first. ETS5 waits for all green tasks._

---

## §4: Integration Contracts

Cross-task data dependencies exist: TASK-ETS1–4 each produce a Python module that
TASK-ETS5 imports to populate the dispatcher registry.

### Contract: PIPELINE_PAYLOAD_CLASSES

- **Producer task:** TASK-ETS1
- **Consumer task:** TASK-ETS5
- **Artifact type:** Python module (`nats_core.events._pipeline`)
- **Format constraint:** All 6 classes (`FeaturePlannedPayload`, `FeatureReadyForBuildPayload`, `BuildStartedPayload`, `BuildProgressPayload`, `BuildCompletePayload`, `BuildFailedPayload`) must be importable from `nats_core.events` and each must be a `BaseModel` subclass with a `model_fields` attribute
- **Validation method:** Seam test `test_pipeline_payload_classes_registered()` in TASK-ETS5 iterates all pipeline `EventType` members and calls `payload_class_for_event_type()`, asserting each returns a Pydantic model

### Contract: AGENT_PAYLOAD_CLASSES

- **Producer task:** TASK-ETS2
- **Consumer task:** TASK-ETS5
- **Artifact type:** Python module (`nats_core.events._agent`)
- **Format constraint:** All 5 classes (`AgentStatusPayload`, `ApprovalRequestPayload`, `ApprovalResponsePayload`, `CommandPayload`, `ResultPayload`) importable from `nats_core.events`; `ERROR` EventType maps to `AgentStatusPayload` (same class as `STATUS`)
- **Validation method:** Seam test `test_agent_payload_classes_registered()` in TASK-ETS5

### Contract: JARVIS_PAYLOAD_CLASSES

- **Producer task:** TASK-ETS3
- **Consumer task:** TASK-ETS5
- **Artifact type:** Python module (`nats_core.events._jarvis`)
- **Format constraint:** All 4 classes (`IntentClassifiedPayload`, `DispatchPayload`, `AgentResultPayload`, `NotificationPayload`) importable from `nats_core.events`
- **Validation method:** Seam test `test_jarvis_payload_classes_registered()` in TASK-ETS5

### Contract: FLEET_PAYLOAD_CLASSES

- **Producer task:** TASK-ETS4
- **Consumer task:** TASK-ETS5
- **Artifact type:** Python modules (`nats_core.events._fleet`, `nats_core.manifest`)
- **Format constraint:** `AgentManifest` (from `nats_core.manifest`) registered for `EventType.AGENT_REGISTER`; `AgentHeartbeatPayload` for `AGENT_HEARTBEAT`; `AgentDeregistrationPayload` for `AGENT_DEREGISTER`
- **Validation method:** Seam test `test_fleet_payload_classes_registered()` in TASK-ETS5

---

## Module Structure

```
src/nats_core/
    __init__.py              # Re-exports all public payload classes
    envelope.py              # MessageEnvelope, EventType, payload_class_for_event_type()
    manifest.py              # AgentManifest, IntentCapability, ToolCapability [TASK-ETS4]
    events/
        __init__.py          # Re-exports all domain payload classes
        _pipeline.py         # 6 pipeline payloads + WaveSummary, TaskProgress [TASK-ETS1]
        _agent.py            # 5 agent payloads [TASK-ETS2]
        _jarvis.py           # 4 Jarvis payloads [TASK-ETS3]
        _fleet.py            # 2 fleet payloads [TASK-ETS4]

tests/
    test_event_type_schemas.py  # 46 BDD scenario tests [TASK-ETS5]
```

---

## Key Design Decisions

### Assumption Decisions

| Assumption | Decision | Rationale |
|------------|----------|-----------|
| ASSUM-007: No max_length on strings | Accept — do NOT add constraints | Spec says "payload should accept the value without constraint"; consumers handle display truncation |
| ASSUM-008: kebab-case agent_id | Implement — `Field(pattern=r"^[a-z][a-z0-9-]*$")` | BDD spec has explicit scenario "Agent registration rejects invalid agent_id format" |

### Naming: AgentRegistrationPayload vs AgentManifest

The BDD spec refers to "AgentRegistrationPayload" but DDR-002 establishes `AgentManifest`
as the full registration payload. Implement as `AgentManifest` per the design contract.
Document this in `src/nats_core/manifest.py` with a docstring note.

### Cross-Field Validators

Two payload classes require Pydantic v2 `@model_validator(mode="after")`:

1. `BuildProgressPayload`: `wave <= wave_total`
2. `BuildCompletePayload`: `tasks_completed + tasks_failed == tasks_total`
3. `FeaturePlannedPayload`: `len(waves) == wave_count`

Use `@model_validator(mode="after")` — do NOT use `@field_validator` for cross-field logic.

### Schema Versioning (ADR-002)

All payload models use `ConfigDict(extra="ignore")` to tolerate forward-compatible
additions. New fields must always be optional with defaults.

---

## Execution Strategy

```
Wave 1 (parallel):
  TASK-ETS1 — Pipeline payloads       → src/nats_core/events/_pipeline.py
  TASK-ETS2 — Agent payloads          → src/nats_core/events/_agent.py
  TASK-ETS3 — Jarvis payloads         → src/nats_core/events/_jarvis.py
  TASK-ETS4 — Fleet payloads/manifest → src/nats_core/events/_fleet.py + manifest.py

Wave 2 (sequential, after Wave 1 complete):
  TASK-ETS5 — Dispatcher + 46 tests  → envelope.py (dispatcher) + tests/test_event_type_schemas.py
```

**Prerequisite check before starting Wave 1:**
- TASK-ME01 status = complete (project scaffolding exists)
- TASK-ME02 status = complete (EventType enum + dispatcher stub exist)

---

## Cross-Feature Dependencies

| This Feature | Depends On | What It Needs |
|-------------|-----------|---------------|
| FEAT-ETS | FEAT-ME (TASK-ME01) | `src/nats_core/events/` sub-package created as empty |
| FEAT-ETS | FEAT-ME (TASK-ME02) | `EventType` enum with all 18 values; `payload_class_for_event_type()` stub |
| FEAT-FR (Fleet Reg) | FEAT-ETS | `AgentManifest`, `IntentCapability`, `ToolCapability` in `manifest.py` |
| FEAT-NC (NATS Client) | FEAT-ETS | All payload classes importable from `nats_core` |
