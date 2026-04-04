# ADR-004: Dynamic Fleet Registration (CAN Bus Pattern)

**Date:** April 2026
**Status:** Accepted

## Context

The original Jarvis design (D15 in jarvis-vision.md) had three options for agent
discovery: static config, dynamic registration via NATS, or agent registry in Graphiti.

The static approach requires updating the Jarvis router code every time a new agent
is added. As the fleet grows (now 8 agents), this becomes a maintenance bottleneck
and violates the open/closed principle.

## Decision

Dynamic registration via NATS, following the CAN bus pattern:

1. Agents publish a capability manifest to `fleet.register` on startup
2. Manifests declare intents (with confidence scores), concurrency limits, and status
3. Jarvis subscribes to `fleet.register`, `fleet.deregister`, and `fleet.heartbeat.>`
4. The routing table is stored in NATS KV (`agent-registry` bucket) for persistence
5. Jarvis routes based on highest confidence match, with queue depth as tiebreaker

This is analogous to devices on a vehicle CAN bus announcing their capabilities
when they power on, or MCP servers advertising their tools.

## Consequences

- Adding a new agent requires NO changes to Jarvis router code
- Agents self-describe their capabilities — single source of truth
- Confidence scoring handles overlapping intents gracefully
- Queue-depth-aware routing enables load balancing across agent instances
- Heartbeat-based liveness detection handles agent failures automatically
- KV-backed registry survives Jarvis restarts without re-registration
- Slightly more complex agent startup (must publish registration)
- Heartbeat infrastructure adds network overhead (minimal — 1 msg per agent per 30s)
