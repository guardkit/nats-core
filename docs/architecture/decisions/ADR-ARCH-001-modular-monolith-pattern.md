# ADR-ARCH-001: Modular Monolith Pattern for Library Organisation

**Date:** 2026-04-07
**Status:** Accepted

## Status

Accepted

## Context

nats-core is a shared contract library consumed by all agents and services in the fleet.
The library needs an internal organisation pattern that balances cohesion (single package
install) with clear module boundaries (independent development of schemas, topics, client).

## Decision

Use a **Modular Monolith** pattern: a single pip-installable package (`nats_core`) with
well-defined internal modules, each owning a distinct responsibility.

Modules follow a unidirectional dependency chain:
```
Config -> Client -> Topics -> Events -> Envelope
```

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| DDD with bounded contexts | Overkill for a library -- bounded contexts make sense for services, not shared schemas |
| Layered architecture | Too rigid -- layers imply strict hierarchy, but consumers need direct access to any module |
| Separate packages per domain | Distribution complexity -- fleet agents would need 4-6 separate pip installs |

## Consequences

- Single `pip install nats-core` for all fleet consumers
- Clear module boundaries prevent tangled imports
- Unidirectional dependency chain prevents circular imports
- Adding new event domains (new files in `events/`) requires no structural changes
- All schemas ship together -- version coherence across event domains
