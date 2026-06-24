# /feature-plan — memory-episode-publisher-canonical-framework-neutral-memorye — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-plan memory-episode-publisher-canonical-framework-neutral-memorye — 2026-06-24T17:05:12Z

### Prompt

```
/feature-plan "Memory episode publisher: canonical framework-neutral MemoryEpisodeV1 Pydantic
schema + publish_episode() helper. Helper validates the schema, sets Nats-Msg-Id=episode_id for
JetStream server-side dedupe, enforces a <=900KB body (reject/split with an actionable error), and
publishes to subject memory.episode.{project_id}.{episode_type}. Add memory.episode.> to the Topics
registry. Tests: round-trip via TestNatsBroker, >900KB rejected, Msg-Id set, subject resolves
correctly. This schema is the cross-repo contract the fleet-memory relay imports (FEAT-MEM-04)."
```

### Assistant response

I'll orchestrate the `/feature-plan` workflow for this NATS memory episode publisher feature. Let me start by grounding the analysis in the actual codebase structure.

Let me examine the key files that this feature will touch — the Topics registry, the client/publish path, envelope, and an existing event module + its tests for patterns.

Now I have the feature brief. This references two cross-repo artifacts — the existing `fleet-memory` schema and the authoritative v2 spec. Let me gather the remaining grounding context in parallel: sibling repos, the envelope, the test patterns (what "TestNatsBroker" means here), and topic test conventions.

Critical finding: **this repo has no FastStream/TestNatsBroker** — it uses raw `nats-py` via `NATSClient`. The brief's "TestNatsBroker" assumes a stack that isn't here. Also, `publish` always wraps in `MessageEnvelope` and neither `publish` nor `publish_raw` supports NATS **headers** (needed for `Nats-Msg-Id`), and `ALL_TOPICS` has a hard-coded count test. These are real design decisions to resolve. Let me read the two existing schema definitions, the v2 spec, the broker test pattern, and the public API.

Let me check how the broker is tested today (the "TestNatsBroker" reconciliation point) and the existing payload-model conventions.

I now have complete grounding. Key technical realities confirmed:

- **No FastStream/TestNatsBroker** — this repo unit-tests with `AsyncMock` over `nats-py`, plus live `@integration` tests against GB10. "TestNatsBroker" must be mapped onto that.
- **`nats-py publish` accepts `headers=`** → `Nats-Msg-Id` is feasible, but neither `NATSClient.publish` nor `publish_raw` passes headers today.
- **The relay consumes RAW `MemoryEpisodeV1` JSON**, not an envelope — so `publish_episode()` must *bypass* `MessageEnvelope`.
- **`ALL_TOPICS` is hard-coupled**: a 5-class tuple + a `== 27` count test will break when a `Memory` namespace is added.
- **Two divergent `MemoryEpisodeV1` schemas** to reconcile per v2 §5.

Given ultracode, I'll run a multi-agent decision-review workflow: independent design analyses of the five contested areas, each adversarially verified against the actual relay/topics/nats-py facts, then synthesized into a task breakdown. This is the `/task-review --mode=decision` analysis, done rigorously.
