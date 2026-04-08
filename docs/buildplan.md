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
| 2 | Feature 1 — Message Envelope `/feature-spec` | **Complete** | 2026-04-08 |
| 2 | Feature 2 — Event Type Schemas `/feature-spec` | **Complete** | 2026-04-08 |
| 2 | Feature 3 — Topic Registry `/feature-spec` | **Complete** | 2026-04-08 |
| 2 | Feature 4 — Configuration `/feature-spec` | **Complete** | 2026-04-08 |
| 2 | Feature 5 — NATS Client `/feature-spec` | **Complete** | 2026-04-08 |
| 2 | Feature 6 — Fleet Registration `/feature-spec` | **Complete** | 2026-04-08 |
| 3 | Feature plans & AutoBuild | Not started | — |

### Decisions Made

| Date | Decision | Context |
|------|----------|---------|
| 2026-04-08 | Feature 1 spec: all 4 groups accepted (A A A A), edge case expansion included (Y), all 3 assumptions confirmed (high confidence) | 23 scenarios total, 0 low-confidence assumptions |
| 2026-04-08 | Feature 2 spec: all 4 groups accepted (A A A A), edge case expansion included (Y), all 8 assumptions confirmed (2 high, 4 medium, 2 low) | 46 scenarios total, 2 low-confidence assumptions (no max_length on strings, kebab-case agent_id) |
| 2026-04-08 | Feature 3 spec: all 4 groups accepted (A A A A), edge case expansion included (Y, 5 additional scenarios), all 5 assumptions confirmed (3 high, 2 medium, 0 low) | 32 scenarios total, 0 low-confidence assumptions |
| 2026-04-08 | Feature 4 spec: all 4 groups accepted (A A A A), edge case expansion included (Y, 4 additional scenarios), all 6 assumptions confirmed (0 high, 3 medium, 3 low) | 23 scenarios total, 3 low-confidence assumptions (all confirmed: user/password pairing, secret masking, auth mutual exclusivity) |
| 2026-04-08 | Feature 5 spec: all 4 groups accepted (A A A A), edge case expansion included (Y, 6 additional scenarios — security, concurrency, integration boundaries), all 4 assumptions confirmed (0 high, 3 medium, 1 low) | 33 scenarios total, 1 low-confidence assumption (confirmed: partial auth is an error) |
| 2026-04-08 | Feature 6 spec: all 4 groups accepted (A A A A), edge case expansion included (Y, 6 additional scenarios — security, concurrency, integration boundaries), all 8 assumptions confirmed (2 high, 5 medium, 1 low) | 28 scenarios total, 1 low-confidence assumption (confirmed: no auth on registration — trust-based CAN bus pattern) |

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

### Feature 1 — Message Envelope (Foundation) — COMPLETE (2026-04-08)

```bash
/feature-spec "Message Envelope: base MessageEnvelope schema with versioning and correlation" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `envelope.py` — MessageEnvelope Pydantic model, UUID v4 message_id defaults,
UTC timestamps, version field, correlation_id for request-response linking,
`extra="ignore"` forward compatibility. No dependencies — this is the foundation.

**Produced:** `features/message-envelope/` — 23 scenarios (5 key, 6 boundary, 4 negative, 8 edge),
3 assumptions (all high confidence, confirmed). 4 smoke scenarios for CI gating.

| File | Description |
|------|-------------|
| `features/message-envelope/message-envelope.feature` | Gherkin spec (23 scenarios) |
| `features/message-envelope/message-envelope_assumptions.yaml` | 3 assumptions manifest |
| `features/message-envelope/message-envelope_summary.md` | Summary for `/feature-plan` |

### Feature 2 — Event Type Schemas — COMPLETE (2026-04-08)

```bash
/feature-spec "Event Type Schemas: typed payloads for pipeline, agent, jarvis, and fleet events" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `events/pipeline.py` (FeaturePlanned, BuildStarted, BuildProgress,
BuildComplete, BuildFailed), `events/agent.py` (AgentStatus, ApprovalRequest,
ApprovalResponse), `events/jarvis.py` (IntentClassified, Dispatch),
`events/fleet.py` (AgentRegistration, AgentHeartbeat, AgentDeregistration,
IntentCapability). EventType enum. Depends on Feature 1 (envelope).

**Produced:** `features/event-type-schemas/` — 46 scenarios (10 key, 14 boundary, 8 negative, 14 edge),
8 assumptions (2 high, 4 medium, 2 low confidence — all confirmed). 10 smoke scenarios for CI gating.

| File | Description |
|------|-------------|
| `features/event-type-schemas/event-type-schemas.feature` | Gherkin spec (46 scenarios) |
| `features/event-type-schemas/event-type-schemas_assumptions.yaml` | 8 assumptions manifest |
| `features/event-type-schemas/event-type-schemas_summary.md` | Summary for `/feature-plan` |

### Feature 3 — Topic Registry — COMPLETE (2026-04-08)

```bash
/feature-spec "Topic Registry: typed constants for all NATS subjects with resolution and project scoping" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `topics.py` — Topics.Pipeline, Topics.Agents, Topics.Jarvis, Topics.Fleet,
Topics.System classes with typed string constants. `resolve()` for template
substitution. `for_project()` for multi-tenancy scoping. No magic strings.
Depends on Feature 2 (event types map to topics).

**Produced:** `features/topic-registry/` — 32 scenarios (8 key, 6 boundary, 5 negative, 13 edge),
5 assumptions (3 high, 2 medium confidence — all confirmed). 8 smoke scenarios for CI gating.

| File | Description |
|------|-------------|
| `features/topic-registry/topic-registry.feature` | Gherkin spec (32 scenarios) |
| `features/topic-registry/topic-registry_assumptions.yaml` | 5 assumptions manifest |
| `features/topic-registry/topic-registry_summary.md` | Summary for `/feature-plan` |

### Feature 4 — Configuration — COMPLETE (2026-04-08)

```bash
/feature-spec "NATS Configuration: pydantic-settings for connection management" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `config.py` — NATSConfig with env_prefix="NATS_", url, timeouts,
reconnect settings, credentials file support, URL scheme validation (nats/tls),
auth mutual exclusivity (user/password vs creds_file), secret masking in
repr/serialisation, .env file loading, nats-py kwargs production.
Independent of other features.

**Produced:** `features/nats-configuration/` — 23 scenarios (5 key, 6 boundary, 8 negative, 8 edge),
6 assumptions (0 high, 3 medium, 3 low confidence — all confirmed). 2 smoke scenarios for CI gating.

| File | Description |
|------|-------------|
| `features/nats-configuration/nats-configuration.feature` | Gherkin spec (23 scenarios) |
| `features/nats-configuration/nats-configuration_assumptions.yaml` | 6 assumptions manifest |
| `features/nats-configuration/nats-configuration_summary.md` | Summary for `/feature-plan` |

### Feature 5 — NATS Client — COMPLETE (2026-04-08)

```bash
/feature-spec "NATS Client: typed publish/subscribe wrapper with automatic envelope handling" \
  --context docs/design/specs/nats-core-system-spec.md
```

Covers: `client.py` — NATSClient wrapping nats-py with typed convenience methods
per event type (publish_build_complete, publish_build_progress, etc.), automatic
MessageEnvelope wrapping/unwrapping, connection with retry, graceful disconnect,
project-scoped publish. Fleet convenience methods (register_agent, deregister_agent,
heartbeat, get_fleet_registry, watch_fleet, call_agent_tool). Depends on
Features 1-4 (envelope, events, topics, config).

**Produced:** `features/nats-client/` — 33 scenarios (8 key, 6 boundary, 6 negative, 13 edge),
4 assumptions (0 high, 3 medium, 1 low confidence — all confirmed). 6 smoke scenarios for CI gating.

| File | Description |
|------|-------------|
| `features/nats-client/nats-client.feature` | Gherkin spec (33 scenarios) |
| `features/nats-client/nats-client_assumptions.yaml` | 4 assumptions manifest |
| `features/nats-client/nats-client_summary.md` | Summary for `/feature-plan` |

### Feature 6 — Fleet Registration (CAN Bus Pattern) — COMPLETE (2026-04-08)

```bash
/feature-spec "Fleet Registration: CAN bus agent discovery with KV-backed routing table" \
  --context docs/design/specs/nats-core-system-spec.md \
  --context docs/design/decisions/ADR-004-dynamic-fleet-registration.md
```

Covers: CAN bus-style dynamic agent discovery — agents self-announce capabilities
on startup via `fleet.register`, maintain liveness via periodic heartbeats to
`fleet.heartbeat.{agent_id}`, and are tracked in a NATS KV-backed routing table
(`agent-registry` bucket). Confidence-based routing with queue-depth tiebreaking.
Concurrency limits via `max_concurrent`. Failure modes including heartbeat timeout,
KV unavailability, and concurrent registration races. Depends on Feature 5 (client).

**Produced:** `features/fleet-registration/` — 28 scenarios (6 key, 6 boundary, 5 negative, 11 edge),
8 assumptions (2 high, 5 medium, 1 low confidence — all confirmed). 3 smoke scenarios for CI gating.

| File | Description |
|------|-------------|
| `features/fleet-registration/fleet-registration.feature` | Gherkin spec (28 scenarios) |
| `features/fleet-registration/fleet-registration_assumptions.yaml` | 8 assumptions manifest |
| `features/fleet-registration/fleet-registration_summary.md` | Summary for `/feature-plan` |

---

## Phase 3: Feature Plans & AutoBuild

After each feature spec is created, run `/feature-plan` with the summary as context, then AutoBuild.

```bash
# Feature 1 (Envelope) — spec complete
/feature-plan "Message Envelope" \
  --context features/message-envelope/message-envelope_summary.md

# Feature 2 (Events) — after feature-spec completes
/feature-plan "Event Type Schemas" \
  --context features/event-type-schemas/event-type-schemas_summary.md

# Feature 3 (Topics) — after feature-spec completes
/feature-plan "Topic Registry" \
  --context features/topic-registry/topic-registry_summary.md

# Feature 4 (Config) — after feature-spec completes
/feature-plan "NATS Configuration" \
  --context features/nats-configuration/nats-configuration_summary.md

# Feature 5 (Client) — after feature-spec completes
/feature-plan "NATS Client" \
  --context features/nats-client/nats-client_summary.md

# Feature 6 (Fleet Reg) — after feature-spec completes
/feature-plan "Fleet Registration" \
  --context features/fleet-registration/fleet-registration_summary.md

# Then for each planned feature:
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
