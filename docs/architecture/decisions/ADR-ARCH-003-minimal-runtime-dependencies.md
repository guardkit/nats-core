# ADR-ARCH-003: Minimal Runtime Dependencies

**Date:** 2026-04-07
**Status:** Accepted

## Status

Accepted

## Context

nats-core is installed as a dependency by every agent and service in the fleet.
Heavy dependencies would inflate install size and increase the risk of version
conflicts across the fleet's dependency trees.

## Decision

Limit runtime dependencies to **three packages only**:
- `nats-py>=2.7.0` -- NATS client
- `pydantic>=2.0` -- schema validation
- `pydantic-settings>=2.0` -- environment-based configuration

All other dependencies (pytest, ruff, mypy) are dev-only.

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Include FastStream | FastStream is for services, not shared libraries -- adds unnecessary weight |
| Include structlog | Logging should be minimal at library level -- consumers choose their own logging |
| Vendor nats-py | Unnecessary complexity -- nats-py is stable and well-maintained |

## Consequences

- Minimal install footprint for all fleet consumers
- Reduced version conflict risk across the fleet
- Library must not use features requiring additional packages
- Any future dependency additions require careful consideration of fleet-wide impact
