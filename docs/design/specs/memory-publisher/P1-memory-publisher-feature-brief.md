# P1 — Memory Episode Publisher (feature brief)

**Date:** 2026-06-24
**Status:** Ready for `/feature-plan` (run from this repo, nats-core)
**Repo:** nats-core (owns the cross-fleet schemas + publisher helper — scope D3)
**Part of:** the post-Graphiti memory write path. Authoritative spec:
`nats-infrastructure/docs/design/specs/memory-relay/memory-write-path-v2-post-graphiti.md` (§5 schema, §6 P1).

## Why this is first

The fleet-memory relay (FEAT-MEM-04, consumer) is built but has **no producer** — nats-core has no
`MemoryEpisodeV1` schema or `publish_episode()` helper today. P1 is the real unblock for the whole
write path and for "run the harvest on the GB10" (the harvest is the first publisher, P4 in guardkit).

## `/feature-plan` input

```
/feature-plan "Memory episode publisher: canonical framework-neutral MemoryEpisodeV1 Pydantic schema
+ publish_episode() helper. Helper validates the schema, sets Nats-Msg-Id=episode_id for JetStream
server-side dedupe, enforces a <=900KB body (reject/split with an actionable error), and publishes to
subject memory.episode.{project_id}.{episode_type}. Add memory.episode.> to the Topics registry.
Tests: round-trip via TestNatsBroker, >900KB rejected, Msg-Id set, subject resolves correctly. This
schema is the cross-repo contract the fleet-memory relay imports (FEAT-MEM-04)."
```

## Scope

- **Canonical `MemoryEpisodeV1`** (Pydantic, `extra="ignore"` for forward-compat). Reconciles the two
  existing definitions (scope-doc 2026-06-12 vs `fleet-memory/src/fleet_memory/relay/schema.py`).
- **`publish_episode(project_id, episode_type, body, ...)`** — validate, `Nats-Msg-Id = episode_id`,
  ≤900 KB guard, publish to `memory.episode.{project_id}.{episode_type}`.
- **Topics registry** entries for `memory.episode.>` (consistent with the existing `Topics` class /
  `topic-registry` feature).
- **Tests** — TestNatsBroker round-trip; >900 KB rejected with actionable error; Msg-Id set; subject
  resolution correct.

## Acceptance criteria (seed)

- [ ] `publish_episode()` round-trips a `MemoryEpisodeV1` against a local/Test NATS broker.
- [ ] Body > 900 KB is rejected (or split) with an actionable error.
- [ ] `Nats-Msg-Id` header set to `episode_id`.
- [ ] Published subject is exactly `memory.episode.{project_id}.{episode_type}`.
- [ ] `memory.episode.>` present in the Topics registry and validated by the topic tests.

## Schema decisions to resolve in planning (v2 §5)

1. **`project_id`** is the canonical key (relay currently uses `project`; renamed in fleet-memory at P3).
2. **`episode_type`** (coarse: adr / feature_outcome / review_report / document / conversation /
   structured_json) vs **`payload_type`** (typed-payload-registry key) — keep both; define the
   relationship and whether `episode_type` drives routing.
3. Which optional fields the writer persists: `name`, `source`, `occurred_at`/`published_at`,
   `ingest_hints`. **Drop** scope-doc `group_id` (FalkorDB-specific; fleet-memory partitions by
   namespace tuple).

## Cross-repo contract note

The schema produced here is imported/mirrored by the fleet-memory relay at P3 (subject corrected to
`memory.episode.>`, `project`→`project_id`, `ack_wait` 60 s). Keep the field set and subject scheme in
lockstep with v2 so producer and consumer agree.

## Downstream (not P1)

P2 nats-infrastructure (MEMORY stream `memory.episode.>`/`memory.dlq.>` + `fleet-memory` NATS user) ·
P3 fleet-memory relay corrections + live verify · P4 guardkit harvest publisher (the GB10 goal).
