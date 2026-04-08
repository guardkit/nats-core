# Feature Spec Summary: Fleet Registration

**Stack**: python
**Generated**: 2026-04-08T00:00:00Z
**Scenarios**: 28 total (3 smoke, 0 regression)
**Assumptions**: 8 total (2 high / 5 medium / 1 low confidence)
**Review required**: Yes

## Scope

Specifies the CAN bus-style dynamic agent discovery protocol where agents self-announce
capabilities on startup, maintain liveness via periodic heartbeats, and are tracked in a
NATS KV-backed routing table. Covers the full lifecycle (register, heartbeat, deregister),
confidence-based routing with queue-depth tiebreaking, concurrency limits via max_concurrent,
and failure modes including heartbeat timeout, KV unavailability, and concurrent registration races.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 6 |
| Boundary conditions (@boundary) | 6 |
| Negative cases (@negative) | 5 |
| Edge cases (@edge-case) | 11 |

## Deferred Items

None.

## Open Assumptions (low confidence)

- ASSUM-007: No authentication mechanism on registration -- any agent can claim any agent_id. Trust-based within network boundary per CAN bus pattern.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Fleet Registration" --context features/fleet-registration/fleet-registration_summary.md
