# Memory Episode Publisher (FEAT-MEP1)

Canonical framework-neutral `MemoryEpisodeV1` Pydantic schema + `publish_episode()` helper for
**nats-core** — P1 of the post-Graphiti memory write path. This is the producer the already-built
`fleet-memory` relay currently lacks.

- **Review:** TASK-REV-MEP1 · **Complexity:** 5/10 · **Tasks:** 5 (3 waves)
- **Spec:** `nats-infrastructure/docs/design/specs/memory-relay/memory-write-path-v2-post-graphiti.md` (§5, §6)
- **Brief:** `docs/design/specs/memory-publisher/P1-memory-publisher-feature-brief.md`
- **Plan details + diagrams:** [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md)

## What gets built

1. **`MemoryEpisodeV1`** (private `src/nats_core/events/_memory.py`, re-exported) — the cross-repo write
   contract; `project_id` key, both `episode_type` + `payload_type`, raw-`str` `content_format`, typed
   optionals, `group_id` dropped, `extra="ignore"`.
2. **`NATSClient.publish_episode(episode)`** — publishes the **raw** model JSON (bypassing
   `MessageEnvelope`) with `Nats-Msg-Id = episode_id` and a **reject-only** ≤900KB guard, to subject
   `memory.episode.{project_id}.{episode_type}`.
3. **`Topics.Memory`** namespace (`EPISODE` template + `memory.episode.>` wildcard), wired into `ALL_TOPICS`.
4. **Tests** — `AsyncMock` unit round-trip + boundary/header/subject coverage; optional live GB10 echo.

## Tasks

| ID | Title | Type | Cx | Mode | Wave | Deps |
|----|-------|------|----|------|------|------|
| TASK-MEP-001 | MemoryEpisodeV1 schema + `MAX_EPISODE_BODY_BYTES` | declarative | 4 | task-work | 1 | — |
| TASK-MEP-002 | `Topics.Memory` namespace + `ALL_TOPICS` wiring | feature | 4 | task-work | 1 | — |
| TASK-MEP-003 | `publish_episode()` helper (raw + header + guard) | feature | 5 | task-work | 2 | 001, 002 |
| TASK-MEP-004 | Unit test suite + `make_memory_episode` factory | testing | 4 | task-work | 3 | 001, 003 |
| TASK-MEP-005 | Optional live `@integration` echo (GB10) | testing | 3 | direct | 3 | 001, 003 |

## Execution

- **Wave 1 (parallel):** TASK-MEP-001 · TASK-MEP-002
- **Wave 2:** TASK-MEP-003
- **Wave 3 (parallel):** TASK-MEP-004 · TASK-MEP-005 *(optional)*

```bash
# Autonomous build
/feature-build FEAT-MEP1

# Or task-by-task
/task-work TASK-MEP-001
/task-work TASK-MEP-002
/task-work TASK-MEP-003
/task-work TASK-MEP-004
```

## ⚠️ Deploy-ordering constraint

The built `fleet-memory` relay still requires a `project` field; this feature emits `project_id` and drops
`project`. A live cross-repo round-trip **breaks until P3 renames `project → project_id`**. P1's own tests
pass (both ends use nats-core's canonical model). Ship P3 together with / immediately after P1, and don't
point a live relay at `memory.episode.*` until P2 (the `MEMORY` stream + `fleet-memory` NATS user) and P3
are in place. See [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) §5 R1.
