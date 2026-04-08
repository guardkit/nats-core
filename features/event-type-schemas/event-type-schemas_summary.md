# Feature Spec Summary: Event Type Schemas

**Stack**: python
**Generated**: 2026-04-08T00:00:00Z
**Scenarios**: 46 total (10 smoke, 0 regression)
**Assumptions**: 8 total (2 high / 4 medium / 2 low confidence)
**Review required**: Yes

## Scope

Typed payload schemas for every event in the system, covering pipeline events (feature planned, build progress, build complete, build failed), agent events (status, approval request/response), Jarvis events (intent classification, dispatch), and fleet registration events (registration, heartbeat, deregistration). The specification validates that all EventType enum members map to a corresponding Pydantic payload class, enforces numeric bounds on progress and confidence fields, constrains Literal-typed status and decision fields, and ensures JSON round-trip fidelity across all payload types.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 10 |
| Boundary conditions (@boundary) | 14 |
| Negative cases (@negative) | 8 |
| Edge cases (@edge-case) | 14 |

## Deferred Items

None.

## Open Assumptions (low confidence)

- ASSUM-007: No max_length constraint on string fields in payload schemas
- ASSUM-008: agent_id must be a kebab-case identifier (pattern: ^[a-z][a-z0-9-]*$)

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Event Type Schemas" --context features/event-type-schemas/event-type-schemas_summary.md
