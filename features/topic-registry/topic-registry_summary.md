# Feature Spec Summary: Topic Registry

**Stack**: python
**Generated**: 2026-04-08T00:00:00Z
**Scenarios**: 32 total (8 smoke, 0 regression)
**Assumptions**: 5 total (3 high / 2 medium / 0 low confidence)
**Review required**: No

## Scope

Typed constants for all NATS subjects across five namespaces (Pipeline, Agents, Fleet, Jarvis, System) with template resolution via `Topics.resolve()` and multi-tenancy project scoping via `Topics.for_project()`. Covers identifier validation to prevent invalid NATS subjects, wildcard topic correctness, and synchronisation between topic templates and the EventType enum.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 8 |
| Boundary conditions (@boundary) | 6 |
| Negative cases (@negative) | 5 |
| Edge cases (@edge-case) | 13 |

## Deferred Items

None.

## Open Assumptions (low confidence)

None.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Topic Registry" --context features/topic-registry/topic-registry_summary.md
