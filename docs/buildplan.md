# nats-core — Build Plan

## GuardKit Command Sequence for Building nats-core

**Repo:** `/Users/richardwoollcott/Projects/appmilla_github/nats-core`
**Template:** `python-library` (already initialised via `guardkit init`)
**Spec:** `docs/design/specs/nats-core-system-spec.md` (6 features, BDD acceptance criteria)

---

## Pre-Flight Check

Before running commands, verify:
- [x] `guardkit init python-library` completed
- [x] Spec merged (no addendum files — Feature 6 fleet registration already in main spec)
- [x] ADRs in place (4 decision records in `docs/design/decisions/`)
- [ ] `pyproject.toml` exists with nats-py + pydantic dependencies
- [ ] `src/nats_core/` package directory exists

---

## Current Status

| Phase | Step | Status | Date |
|-------|------|--------|------|
| 1 | `/system-arch` | **Complete** | 2026-04-07 |
| 1 | `/system-design` | Not started | — |
| 2 | Feature specs (1-6) | Not started | — |
| 3 | Feature plans & AutoBuild | Not started | — |

---

## Phase 1: Architecture & Design

nats-core is a library with behavioural contracts, so it benefits from the full
`/system-arch` → `/system-design` pipeline to produce proper architecture docs,
component boundaries, and detailed design contracts before feature implementation.

### Step 1: System Architecture — COMPLETE (2026-04-07)

```bash
/system-arch \
  --from docs/design/specs/nats-core-system-spec.md \
  --context docs/design/decisions/ADR-001-nats-as-event-bus.md \
  --context docs/design/decisions/ADR-004-dynamic-fleet-registration.md
```

**Produced:** `docs/architecture/` — C4 diagrams, domain model, assumptions, 3 ADRs.
All artefacts seeded to Graphiti (68 nodes, 87 edges).

**Key decisions:**
- **Structural Pattern:** Modular Monolith — single cohesive package with 6 modules
- **Python Version:** >=3.12 (matching fleet minimum, not template default of 3.10)
- **Dependencies:** Zero runtime deps beyond nats-py + pydantic + pydantic-settings
- **CI/CD:** GitHub Actions (pytest, ruff, mypy strict)
- **Module dependency chain:** `Config → Client → Topics → Events → Envelope`

**Artefacts created:**
| File | Description |
|------|-------------|
| `docs/architecture/ARCHITECTURE.md` | Index + summary |
| `docs/architecture/domain-model.md` | Entities, relationships, topic structure |
| `docs/architecture/system-context.md` | C4 Level 1 diagram |
| `docs/architecture/container.md` | C4 Level 2 diagram |
| `docs/architecture/assumptions.yaml` | 10 assumptions to validate |
| `docs/architecture/decisions/ADR-ARCH-001-modular-monolith-pattern.md` | Modular Monolith for library organisation |
| `docs/architecture/decisions/ADR-ARCH-002-python-312-minimum.md` | Python 3.12+ minimum version |
| `docs/architecture/decisions/ADR-ARCH-003-minimal-runtime-dependencies.md` | Zero runtime deps beyond nats-py + pydantic |

### Step 2: System Design

```bash
/system-design \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/design/specs/nats-core-system-spec.md \
  --context docs/design/decisions/ADR-002-schema-versioning.md \
  --context docs/design/decisions/ADR-003-nats-py-vs-faststream.md
```

Produces: `docs/design/DESIGN.md` — detailed design contracts, data models,
module interfaces, Pydantic schema definitions, topic registry API.

---

## Phase 2: Feature Specs (6 features)

Each feature uses `/feature-spec` because nats-core has behavioural contracts
that benefit from BDD scenarios (specification by example with Gherkin).

### Feature 1 — Message Envelope (Foundation)

```bash
/feature-spec "Message Envelope: base MessageEnvelope schema with versioning and correlation" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `envelope.py` — MessageEnvelope Pydantic model, UUID v4 message_id defaults,
UTC timestamps, version field, correlation_id for request-response linking,
`extra="ignore"` forward compatibility. No dependencies — this is the foundation.

### Feature 2 — Event Type Schemas

```bash
/feature-spec "Event Type Schemas: typed payloads for pipeline, agent, jarvis, and fleet events" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `events/pipeline.py` (FeaturePlanned, BuildStarted, BuildProgress,
BuildComplete, BuildFailed), `events/agent.py` (AgentStatus, ApprovalRequest,
ApprovalResponse), `events/jarvis.py` (IntentClassified, Dispatch),
`events/fleet.py` (AgentRegistration, AgentHeartbeat, AgentDeregistration,
IntentCapability). EventType enum. Depends on Feature 1 (envelope).

### Feature 3 — Topic Registry

```bash
/feature-spec "Topic Registry: typed constants for all NATS subjects with resolution and project scoping" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `topics.py` — Topics.Pipeline, Topics.Agents, Topics.Jarvis, Topics.Fleet,
Topics.System classes with typed string constants. `resolve()` for template
substitution. `for_project()` for multi-tenancy scoping. No magic strings.
Depends on Feature 2 (event types map to topics).

### Feature 4 — Configuration

```bash
/feature-spec "NATS Configuration: pydantic-settings for connection management" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `config.py` — NATSConfig with env_prefix="NATS_", url, timeouts,
reconnect settings, credentials file support. Independent of other features.

### Feature 5 — NATS Client

```bash
/feature-spec "NATS Client: typed publish/subscribe wrapper with automatic envelope handling" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `client.py` — NATSClient wrapping nats-py with typed convenience methods
per event type (publish_build_complete, publish_build_progress, etc.), automatic
MessageEnvelope wrapping/unwrapping, connection with retry, graceful disconnect,
project-scoped publish. Depends on Features 1-4 (envelope, events, topics, config).

### Feature 6 — Fleet Registration (CAN Bus Pattern)

```bash
/feature-spec "Fleet Registration: CAN bus agent discovery with KV-backed routing table" \
  --context docs/design/specs/nats-core-system-spec.md \
  --context docs/design/decisions/ADR-004-dynamic-fleet-registration.md
```

Covers: NATSClient convenience methods — `register_agent()`, `deregister_agent()`,
`heartbeat()`, `get_fleet_registry()`, `watch_fleet()`. AgentRegistrationPayload
with IntentCapability list and confidence scores. KV bucket interaction for
`agent-registry`. Heartbeat lifecycle. Depends on Feature 5 (client).

---

## Phase 3: Feature Plans & AutoBuild

After all feature specs are created, run `/feature-plan` for each, then AutoBuild.

```bash
# For each feature (1-6):
/feature-plan
# Review the generated task breakdown
# Then:
autobuild
```

### Build Order (Dependency Chain)

```
Feature 1 (Envelope)     ← foundation, no deps
Feature 4 (Config)       ← independent, no deps
Feature 2 (Events)       ← depends on Feature 1
Feature 3 (Topics)       ← depends on Feature 2
Feature 5 (Client)       ← depends on Features 1, 2, 3, 4
Feature 6 (Fleet Reg)    ← depends on Feature 5
```

Features 1 and 4 can be built in parallel. Feature 2 and 3 are sequential.
Feature 5 integrates everything. Feature 6 adds the CAN bus layer on top.

---

## Key Files Produced

```
nats-core/
├── docs/
│   ├── architecture/ARCHITECTURE.md    ← from /system-arch
│   └── design/
│       ├── DESIGN.md                   ← from /system-design
│       ├── specs/nats-core-system-spec.md  ← input (already exists)
│       ├── contracts/                  ← from /system-design
│       └── decisions/ADR-001..004      ← already exist
├── src/nats_core/
│   ├── __init__.py
│   ├── py.typed
│   ├── envelope.py                     ← Feature 1
│   ├── config.py                       ← Feature 4
│   ├── events/
│   │   ├── __init__.py
│   │   ├── pipeline.py                 ← Feature 2
│   │   ├── agent.py                    ← Feature 2
│   │   ├── jarvis.py                   ← Feature 2
│   │   └── fleet.py                    ← Feature 2 + 6
│   ├── topics.py                       ← Feature 3
│   └── client.py                       ← Feature 5 + 6
├── tests/
│   ├── test_envelope.py                ← Feature 1
│   ├── test_events.py                  ← Feature 2
│   ├── test_topics.py                  ← Feature 3
│   ├── test_config.py                  ← Feature 4
│   ├── test_client.py                  ← Feature 5
│   ├── test_fleet.py                   ← Feature 6
│   └── test_integration.py            ← -m integration
└── pyproject.toml
```

---

## Validation

After all features are built:

```bash
# Unit tests (no NATS server needed)
pytest

# Type checking
mypy src/

# Lint
ruff check .

# Integration tests (requires NATS — use nats-infrastructure docker compose)
pytest -m integration
```
