# nats-core Architecture

**Generated:** 2026-04-07
**Pattern:** Modular Monolith (shared library)
**Language:** Python >=3.12

---

## Overview

nats-core is the shared contract layer for the Jarvis Ship's Computer fleet. A pip-installable
Python library providing message envelope schemas, event type schemas, a topic registry,
a typed NATS client, and multi-tenancy support.

Every agent, adapter, and service in the fleet depends on this library. Schema changes
require semver coordination.

## Structural Pattern

**Modular Monolith** -- a single cohesive package (`nats_core`) with well-defined internal
modules. Each module has clear responsibilities and a unidirectional dependency chain:

```
Config -> Client -> Topics -> Events -> Envelope
                               |
                           Manifest
```

## Modules

| Module | Path | Responsibility |
|--------|------|---------------|
| Envelope | `envelope.py` | `MessageEnvelope` base schema -- wire format for all NATS messages |
| Events | `events/` | Typed payload schemas per domain (pipeline, agent, jarvis, fleet) |
| Manifest | `manifest.py` | `AgentManifest`, `IntentCapability`, `ToolCapability` |
| Topics | `topics.py` | Topic registry -- typed constants, resolution, project scoping |
| Client | `client.py` | `NATSClient` -- typed pub/sub wrapper, fleet convenience methods |
| Config | `config.py` | `NATSConfig` via pydantic-settings (env vars) |

## Consumers

| Consumer Type | Usage |
|---------------|-------|
| Agent services (Jarvis, PO Agent, Architect, etc.) | Import models, pub/sub via `NATSClient` |
| Adapters (Telegram, Reachy Bridge, CLI) | Import Jarvis event schemas, publish commands |
| Pipeline orchestrators (GuardKit Factory) | Import pipeline event schemas, publish build events |
| Test suites (fleet-wide) | Import models for assertions, mock data factories |

## Cross-Cutting Concerns

| Concern | Approach |
|---------|----------|
| Authentication | Delegated to NATS server -- `NATSConfig` provides credentials |
| Logging | stderr-only structured logging (never print()) |
| Error Handling | Pydantic `ValidationError` for schemas, nats-py errors bubbled with retry |
| Data Validation | Pydantic models at all boundaries, `extra="ignore"` for forward compat |
| Schema Versioning | `version` field in envelope + semver on package |
| Correlation | `correlation_id` in envelope links related messages |

## Quality Constraints

| Constraint | Target |
|------------|--------|
| Runtime dependencies | nats-py + pydantic + pydantic-settings only |
| Type coverage | 100% (py.typed, mypy strict) |
| Unit test isolation | All unit tests run without NATS server |
| Versioning | Semver (breaking changes = major bump) |
| Python version | >=3.12 |

## Architecture Documents

- [Domain Model](domain-model.md)
- [C4 System Context](system-context.md)
- [C4 Container Diagram](container.md)
- [Assumptions](assumptions.yaml)

### Architecture Decision Records

- [ADR-ARCH-001: Modular Monolith pattern](decisions/ADR-ARCH-001-modular-monolith-pattern.md)
- [ADR-ARCH-002: Python 3.12+ minimum](decisions/ADR-ARCH-002-python-312-minimum.md)
- [ADR-ARCH-003: Minimal runtime dependencies](decisions/ADR-ARCH-003-minimal-runtime-dependencies.md)

### Related Design Decisions (upstream)

- [ADR-001: NATS as Event Bus](../design/decisions/ADR-001-nats-as-event-bus.md)
- [ADR-004: Dynamic Fleet Registration](../design/decisions/ADR-004-dynamic-fleet-registration.md)
