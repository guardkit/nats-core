# ADR-001: NATS as Event Bus

**Date:** February 2026
**Status:** Accepted (inherited from Dev Pipeline System Spec ADR-SP-001)

## Context

The Ship's Computer fleet needs a message bus for event-driven agent coordination.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Kafka** | Industry standard, massive ecosystem | Complex (Zookeeper/KRaft), overkill for single-developer |
| **NATS JetStream** | Single binary, sub-ms latency, built-in persistence + KV | Smaller ecosystem |
| **Redis Streams** | Familiar, lightweight | No built-in account isolation, weaker persistence |

## Decision

NATS with JetStream as the sole message bus for all fleet communication.

## Consequences

- Single binary deployment — no cluster management
- Sub-millisecond latency — critical for real-time voice interaction with Reachy Mini
- Built-in KV store for agent state (no separate Redis needed)
- Native account isolation for multi-tenancy (FinProxy scoping)
- Smaller community than Kafka — but adequate for our scale
