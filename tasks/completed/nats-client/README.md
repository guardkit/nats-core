# NATS Client Feature

**Feature ID:** FEAT-1T1W
**Review task:** TASK-1T1W
**Status:** Planned
**Complexity:** 7/10

## Summary

Typed publish/subscribe wrapper around nats-py providing automatic `MessageEnvelope`
wrapping/unwrapping, topic resolution, multi-tenancy, fleet registration convenience
methods, and agent-to-agent tool invocation via request-reply.

## Tasks

| ID | Title | Type | Complexity | Wave | Status |
|----|-------|------|------------|------|--------|
| TASK-NC01 | NATSConfig + AgentConfig models | declarative | 2 | 1 | pending |
| TASK-NC02 | Topics registry | declarative | 3 | 1 | pending |
| TASK-NC03 | Event payload models | declarative | 3 | 2 | pending |
| TASK-NC04 | AgentManifest + ManifestRegistry | declarative | 4 | 3 | pending |
| TASK-NC05 | NATSClient core (connect/pub/sub) | feature | 6 | 4 | pending |
| TASK-NC06 | Fleet methods + NATSKVManifestRegistry | feature | 5 | 5 | pending |
| TASK-NC07 | call_agent_tool (request-reply) | feature | 4 | 5 | pending |
| TASK-NC08 | Unit tests (declarative modules) | testing | 4 | 6 | pending |
| TASK-NC09 | Integration tests (33 BDD scenarios) | testing | 6 | 6 | pending |

## Prerequisites

- **TASK-ME01** (project scaffolding) — must be complete before wave 1
- **TASK-ME02** (MessageEnvelope model) — must be complete before wave 2

## Execution Order

```
Wave 1:  [NC01, NC02]          ← parallel, no NATS needed
Wave 2:  [NC03]                ← after ME02
Wave 3:  [NC04]                ← after NC03
Wave 4:  [NC05]                ← critical path
Wave 5:  [NC06, NC07]          ← parallel, after NC05
Wave 6:  [NC08, NC09]          ← parallel; NC09 needs NATS server
```

## Key Design Decisions

- **nats-py only** (ADR-003) — no FastStream, no additional broker abstractions
- **Dynamic Fleet Registration** (ADR-004) — NATS KV `agent-registry` bucket
- **AgentConfig is local** — never serialised into AgentManifest, never published
- **All published messages auto-wrapped** in `MessageEnvelope` by `NATSClient.publish()`

## Feature Spec

- `features/nats-client/nats-client.feature` — 33 BDD scenarios
- `features/nats-client/nats-client_summary.md` — summary and deferred items

## Implementation Guide

See [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) for:
- Data flow diagrams (read/write paths)
- Integration contract diagrams (publish sequence)
- Task dependency graph
- §4 Integration Contracts
- Risk register
