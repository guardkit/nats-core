# ADR-003: nats-py for Core Library, FastStream for Services

**Date:** April 2026
**Status:** Accepted

## Context

Two Python NATS libraries exist: `nats-py` (official low-level client) and `FastStream`
(high-level framework with broker patterns). Need to decide which nats-core uses.

## Decision

- **nats-core** uses `nats-py` — it's a library, not a service. Minimal dependencies,
  maximum flexibility for consumers.
- **Individual services** (adapters, agents) use `FastStream[nats]` — they benefit from
  the handler/subscriber patterns, TestNatsBroker for unit testing, and lifespan management.
- Both import schemas and topic constants from nats-core.

## Consequences

- nats-core has minimal dependencies (nats-py + pydantic only)
- Services get FastStream's TestNatsBroker for infrastructure-free unit tests
- The NATSClient in nats-core wraps nats-py directly
- Services that need raw JetStream features (KV watch, custom streams) can drop
  to nats-py through nats-core's client without fighting FastStream abstractions
