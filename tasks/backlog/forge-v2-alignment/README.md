# nats-core Forge v2.2 Alignment

**Parent review:** `forge/tasks/backlog/TASK-REV-A1F2-align-forge-build-plan-docs.md`
**Alignment report:** `forge/docs/research/forge-build-plan-alignment-review.md`
**Driving ADRs:** [ADR-SP-014 Jarvis trigger](../../../forge/docs/research/forge-pipeline-architecture.md), [ADR-SP-016 singular topics](../../../forge/docs/research/forge-pipeline-architecture.md)

## Problem

TASK-REV-A1F2 audited `nats-core` and found it 98% test-covered on what exists, but **missing the v2.2-critical pipeline payloads and topics that Forge depends on**. The anchor assumes these exist; the forge build plan claims nats-core is "✅ implemented"; reality is that four payloads and five topics are absent and one legacy payload is stale.

## Missing items (source: alignment review §2.1)

- `BuildQueuedPayload` — **CRITICAL**, Forge cannot start without this
- `BuildPausedPayload` — **CRITICAL**, 🟡 confidence gates depend on it
- `BuildResumedPayload` — HIGH, required for pause/resume flow
- `StageCompletePayload` — HIGH, per-stage progress signal
- `StageGatedPayload` — HIGH, differentiates 🟡 gated from ✅ completed
- Topic `pipeline.build-queued.{feature_id}`
- Topic `pipeline.build-paused.{feature_id}`
- Topic `pipeline.build-resumed.{feature_id}`
- Topic `pipeline.stage-complete.{feature_id}`
- Topic `pipeline.stage-gated.{feature_id}`
- Topic `agents.command.broadcast` (singular, per ADR-SP-016)

## Stale items to retire

- `FeaturePlannedPayload` (`src/nats_core/events/_pipeline.py:56`) — superseded by `BuildQueuedPayload`, anchor §11 lists as removed
- Topic `pipeline.feature-planned.{feature_id}` (`src/nats_core/topics.py:79`) — same

`FeatureReadyForBuildPayload` + its topic are left as-is pending coordination with TASK-FVD3 (orchestrator-refresh decision).

## Topic convention (ADR-SP-016)

nats-core's current **singular** convention (`agents.command.{agent_id}`, `agents.result.{agent_id}`) is now the fleet-wide standard. No renames — the anchor has been updated to match. This task only needs to **add** the new `COMMAND_BROADCAST = "agents.command.broadcast"` constant alongside the existing singular entries.

## Scope — Subtasks

| Task | Changes | Depends on |
|------|---------|-----------|
| TASK-NCFA-001 | Add five new pipeline payloads (Build{Queued,Paused,Resumed}, Stage{Complete,Gated}) with validators; add five new topics to `Topics.Pipeline` and `agents.command.broadcast` to `Topics.Agents`; retire `FeaturePlannedPayload` + its topic (deprecate with warning, removal in next minor) | — |
| TASK-NCFA-002 | Integration tests for every new payload against live NATS on GB10 — publish, envelope round-trip, schema validation, forward-compat of `extra='allow'`, correlation ID threading through `BuildStarted/Progress/Complete` | TASK-NCFA-001 |

## Out of scope

- Renaming any existing topic or payload — nats-core's singular convention is now canonical
- Adding Jarvis-specific topics (`jarvis.dispatch.*`, `jarvis.session.*`) — those live in the `jarvis` repo once it has code
- Changing `MessageEnvelope` or `NATSClient` — only adding payload + topic constants on top
- Any infrastructure change in `nats-infrastructure` (streams already provisioned; no new streams needed for these topics since they all land in the existing `PIPELINE` stream)
