# Implementation Guide: NATS Client

**Feature:** NATS Client (`FEAT-1T1W`)
**Review task:** TASK-1T1W
**Approach:** Layered Declarative-First Build
**Estimated effort:** 3–4 days
**Overall complexity:** 7/10

---

## Data Flow: Read/Write Paths

```mermaid
flowchart LR
    subgraph Writes["Write Paths"]
        W1["NATSClient.publish()"]
        W2["NATSClient.register_agent()"]
        W3["NATSClient.deregister_agent()"]
        W4["NATSClient.heartbeat()"]
        W5["NATSClient.call_agent_tool()\n(request)"]
    end

    subgraph Storage["Transport & Storage"]
        S1[("NATS Server\npub/sub broker")]
        S2[("JetStream KV\nagent-registry")]
    end

    subgraph Reads["Read Paths"]
        R1["subscribe() handler\n→ MessageEnvelope"]
        R2["get_fleet_registry()\n→ dict[str, AgentManifest]"]
        R3["watch_fleet() callback\n→ AgentManifest | None"]
        R4["call_agent_tool() reply\n→ Any (JSON)"]
    end

    W1 -->|"envelope.model_dump_json()"| S1
    W2 -->|"fleet.register topic"| S1
    W2 -->|"KV.put(agent_id)"| S2
    W3 -->|"fleet.deregister topic"| S1
    W3 -->|"KV.delete(agent_id)"| S2
    W4 -->|"fleet.heartbeat.{id}"| S1
    W5 -->|"agents.{id}.tools.{tool}\n(NATS request)"| S1

    S1 -->|"nats-py msg callback"| R1
    S2 -->|"KV.get_all()"| R2
    S2 -->|"KV.watch()"| R3
    S1 -->|"NATS reply msg"| R4
```

_All write paths have a corresponding read path. No disconnections._

---

## Integration Contracts: Publish Path

```mermaid
sequenceDiagram
    participant Caller as Fleet Agent
    participant Client as NATSClient.publish()
    participant Topics as Topics.resolve()
    participant Env as MessageEnvelope
    participant NATS as nats-py / NATS Server
    participant Handler as Subscriber Callback

    Caller->>Client: publish(topic, payload, event_type, source_id, project?)
    Client->>Topics: for_project(project, topic) if project set
    Topics-->>Client: scoped topic string
    Client->>Env: construct(message_id=uuid4, timestamp=now,\nversion="1.0", source_id, event_type, payload.model_dump())
    Env-->>Client: MessageEnvelope instance
    Client->>NATS: nc.publish(topic, envelope.model_dump_json().encode())
    NATS-->>Handler: raw bytes
    Handler->>Env: MessageEnvelope.model_validate_json(raw)
    Env-->>Handler: typed MessageEnvelope

    Note over Handler: On ValidationError or JSONDecodeError:<br/>log to stderr, do NOT propagate
```

_Key: `payload.model_dump()` goes into `envelope.payload` — it cannot override envelope-level fields._

---

## Task Dependencies

```mermaid
graph TD
    ME01["TASK-ME01\nProject Scaffolding\n(prerequisite)"]
    ME02["TASK-ME02\nMessageEnvelope\n(prerequisite)"]

    NC01["TASK-NC01\nNATSConfig + AgentConfig\n(declarative, wave 1)"]
    NC02["TASK-NC02\nTopics Registry\n(declarative, wave 1)"]
    NC03["TASK-NC03\nEvent Payload Models\n(declarative, wave 2)"]
    NC04["TASK-NC04\nAgentManifest + Registry\n(declarative, wave 3)"]
    NC05["TASK-NC05\nNATSClient Core\n(feature, wave 4)"]
    NC06["TASK-NC06\nFleet Methods + KV\n(feature, wave 5)"]
    NC07["TASK-NC07\ncall_agent_tool\n(feature, wave 5)"]
    NC08["TASK-NC08\nUnit Tests\n(testing, wave 6)"]
    NC09["TASK-NC09\nIntegration Tests\n(testing, wave 6)"]

    ME01 --> NC01
    ME01 --> NC02
    ME02 --> NC03
    ME02 --> NC05

    NC01 --> NC05
    NC02 --> NC05
    NC03 --> NC04
    NC03 --> NC08
    NC04 --> NC06
    NC04 --> NC08
    NC05 --> NC06
    NC05 --> NC07
    NC05 --> NC09
    NC06 --> NC09
    NC07 --> NC09
    NC01 --> NC08
    NC02 --> NC08

    style NC01 fill:#cfc,stroke:#090
    style NC02 fill:#cfc,stroke:#090
    style NC06 fill:#cfc,stroke:#090
    style NC07 fill:#cfc,stroke:#090
    style NC08 fill:#cfc,stroke:#090
    style NC09 fill:#cfc,stroke:#090
```

_Green tasks can run in parallel within their wave._

---

## §4: Integration Contracts

### Contract: NATSConfig Python API

- **Producer task:** TASK-NC01
- **Consumer task(s):** TASK-NC05
- **Artifact type:** Python module (`nats_core.config.NATSConfig`)
- **Format constraint:** `NATSConfig()` must instantiate without args using env var defaults; must expose `url: str`, `connect_timeout: float`, `max_reconnect_attempts: int`, `reconnect_time_wait: float`, `name: str`, `user: str | None`, `password: str | None`, `creds_file: str | None` — all passed directly to `nats.connect()`
- **Validation method:** Coach verifies NC05 imports `NATSConfig` and all fields are used in `connect()` call; seam test in NC05 checks field types

### Contract: Topics Python API

- **Producer task:** TASK-NC02
- **Consumer task(s):** TASK-NC05, TASK-NC06, TASK-NC07
- **Artifact type:** Python module (`nats_core.topics.Topics`)
- **Format constraint:** `Topics.resolve(template, **kwargs) -> str` — no `{placeholder}` tokens in output; raises `KeyError` on missing kwargs, `ValueError` on wildcard chars; `Topics.for_project(project, topic) -> str` prepends `{project}.`
- **Validation method:** Coach verifies NC05 calls `Topics.for_project()` when `project` arg is set; seam tests in NC05 verify resolution output format

### Contract: MessageEnvelope Python API

- **Producer task:** TASK-ME02
- **Consumer task(s):** TASK-NC03, TASK-NC05
- **Artifact type:** Python module (`nats_core.envelope.MessageEnvelope`, `nats_core.envelope.EventType`)
- **Format constraint:** `MessageEnvelope.model_dump_json()` → valid JSON string; `MessageEnvelope.model_validate_json(raw: bytes | str)` → typed instance; `EventType` enum values match wire format event type strings (snake_case)
- **Validation method:** Seam test in NC03 and NC05 verifies round-trip JSON encoding; NC05 constructs envelope with all required fields

### Contract: AgentManifest Python API

- **Producer task:** TASK-NC04
- **Consumer task(s):** TASK-NC06
- **Artifact type:** Python module (`nats_core.manifest.AgentManifest`, `nats_core.manifest.ManifestRegistry`)
- **Format constraint:** `AgentManifest.model_dump_json().encode()` → UTF-8 bytes valid for NATS KV put; `AgentManifest.model_validate_json(raw_bytes)` → typed instance for `get_fleet_registry()` deserialization
- **Validation method:** Seam test in NC06 verifies encode→decode round-trip; Coach verifies `NATSKVManifestRegistry` implements all `ManifestRegistry` abstract methods

### Contract: NATSClient Core API

- **Producer task:** TASK-NC05
- **Consumer task(s):** TASK-NC06, TASK-NC07
- **Artifact type:** Python class (`nats_core.client.NATSClient`)
- **Format constraint:** `NATSClient._nc` must be non-None after `connect()`; fleet methods and `call_agent_tool()` access JetStream via `_nc.jetstream()` and request/reply via `_nc.request()`; all methods must raise `RuntimeError("client is not connected")` when `_nc is None`
- **Validation method:** Seam tests in NC06 and NC07 verify `_nc` initial state; Coach verifies all new methods guard on `_nc is None` before use

---

## Execution Waves

| Wave | Tasks | Can Parallelise? | NATS Server Needed? |
|------|-------|-----------------|---------------------|
| Pre | TASK-ME01, TASK-ME02 | Yes | No |
| 1 | NC01, NC02 | Yes | No |
| 2 | NC03 | Single | No |
| 3 | NC04 | Single | No |
| 4 | NC05 | Single (critical path) | Yes (for manual testing) |
| 5 | NC06, NC07 | Yes | Yes |
| 6 | NC08, NC09 | Yes | NC09 needs NATS |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| nats-py KV watch API changes between versions | Low | Medium | Pin nats-py version; check `nats-py>=2.4.0` for KV support |
| Slow consumer backpressure hard to test | Medium | Low | Use nats-py mock or integration test skip marker |
| Reconnection window message loss hard to simulate | Medium | Medium | Mark edge-case tests; use `nats-server -js` with Docker for controlled disconnection |
| `watch_fleet()` async iterator leaks if not cancelled | Medium | Medium | Document `asyncio.create_task()` pattern; add cancellation test to NC09 |
| Concurrent KV register+deregister race | Low | Medium | NATS KV is sequentially consistent per key — document this guarantee |

---

## Architecture Constraints

- **ADR-003:** `NATSClient` wraps nats-py only — no FastStream, no aioredis, no other broker
- **ADR-004:** Dynamic Fleet Registration via NATS KV `agent-registry` bucket
- **Dependency direction:** `Config → Client → Topics → Events → Envelope` (no upward imports)
- **`AgentConfig` isolation:** Never appears in `AgentManifest`, never published to fleet
- **Error handling:** All subscriber errors go to `stderr` via `logging` — never `print()`

---

## Quick Start

```bash
# Prerequisites
pip install -e ".[dev]"

# Start NATS with JetStream (for integration tests)
nats-server -js

# Run unit tests (no NATS required)
pytest tests/ -m unit -v

# Run smoke integration tests
pytest tests/ -m "smoke and integration" -v

# Run full suite
pytest tests/ -v --cov=src/nats_core --cov-report=term-missing
```
