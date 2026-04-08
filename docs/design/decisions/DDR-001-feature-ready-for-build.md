# DDR-001: Replace READY_FOR_DEV with FEATURE_READY_FOR_BUILD

**Date:** 2026-04-07
**Status:** Accepted
**Related Components:** Message Contracts, Topic Registry

---

## Context

The original `READY_FOR_DEV` event was modelled after Kanban card movement by a
PM tool webhook. In the context-first pipeline, there are no tickets and no PM
tool -- features are ready for build when the Pipeline Orchestrator Agent
completes a GuardKit command sequence, not when a human moves a card.

The `TICKET_UPDATED` event similarly assumed a ticket tracking system that does
not exist in this pipeline architecture.

## Decision

1. Replace `READY_FOR_DEV` EventType with `FEATURE_READY_FOR_BUILD`
2. Drop `TICKET_UPDATED` EventType entirely
3. New `FeatureReadyForBuildPayload` carries artefact paths, not ticket IDs

## Rationale

The trigger for build readiness is the Pipeline Orchestrator completing:
- Greenfield: `/system-arch` -> `/system-design` -> `/system-plan`
- Existing: `/feature-spec` -> `/feature-plan`

The payload must carry the output artefact paths (`spec_path`, `plan_path`,
`pipeline_type`) that AutoBuild needs to begin work. A ticket ID is meaningless
in this context.

## Alternatives Considered

- **Keep READY_FOR_DEV with different payload** -- confusing name implies external
  trigger (a "dev" picking up work), not an orchestrator emitting a signal
- **Add webhook integration later** -- YAGNI, no ticket system exists or is planned

## Consequences

- Topic changes: `pipeline.ready-for-dev.{feature_id}` ->
  `pipeline.feature-ready-for-build.{feature_id}`
- Clearer semantics: event name matches its actual trigger
- AutoBuild receives artefact paths directly, no lookup needed
- `TICKET_UPDATED` removed from EventType enum (6 pipeline events, was 7)
