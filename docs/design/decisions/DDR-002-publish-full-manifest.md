# DDR-002: Publish Full AgentManifest for Fleet Registration

**Date:** 2026-04-07
**Status:** Accepted
**Related Components:** Fleet Registration, NATS Client

---

## Context

The original design had a separate `AgentRegistrationPayload` that wrapped
`AgentManifest` with additional fields (container_id, startup metadata). This
created two models for the same concept -- the capability declaration published
on agent startup.

## Decision

Drop `AgentRegistrationPayload`. Publish `AgentManifest` directly as the
`MessageEnvelope.payload` on `fleet.register`. The NATS KV store holds the
same `AgentManifest` object that was published.

## Rationale

- Single model, no duplication -- one Pydantic class to maintain
- `container_id` and `metadata` already exist on `AgentManifest`
- KV stores the same object that was published (no translation layer)
- `AgentManifest.status` covers the startup state (`"starting"` -> `"ready"`)
- MCP tool derivation reads from the same model stored in KV

## Alternatives Considered

- **Keep separate AgentRegistrationPayload** -- allows independent evolution of
  registration vs capability schemas, but in practice they always change together
- **Embed manifest in payload dict** -- hybrid approach, adds extraction complexity
  with no clear benefit

## Consequences

- `AgentRegistrationPayload` removed from `events/fleet.py`
- `fleet.register` topic carries `AgentManifest` in `MessageEnvelope.payload`
- `NATSKVManifestRegistry.register()` stores `AgentManifest` directly
- Agents that re-register (e.g., after config change) publish an updated manifest
- Slightly larger registration message (full manifest vs subset), but negligible
  at fleet scale (<10 agents)
