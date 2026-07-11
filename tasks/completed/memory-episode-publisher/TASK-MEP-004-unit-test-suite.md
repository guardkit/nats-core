---
id: TASK-MEP-004
title: Unit test suite — MemoryEpisodeV1, publish_episode, make_memory_episode factory
status: completed
completed: '2026-06-24T00:00:00+00:00'
created: 2026-06-24 00:00:00+00:00
updated: '2026-06-24T00:00:00+00:00'
priority: high
task_type: testing
tags:
- memory-publisher
- tests
- pytest
- factory
complexity: 4
wave: 3
implementation_mode: task-work
parent_review: TASK-REV-MEP1
feature_id: FEAT-MEP1
dependencies:
- TASK-MEP-001
- TASK-MEP-003
consumer_context:
- task: TASK-MEP-001
  consumes: MemoryEpisodeV1
  framework: Pydantic BaseModel (nats_core.events._memory)
  driver: pydantic
  format_note: Tests construct and round-trip MemoryEpisodeV1; the factory builds
    bodies just over/under MAX_EPISODE_BODY_BYTES via a body override.
- task: TASK-MEP-003
  consumes: NATSClient.publish_episode
  framework: AsyncMock over nats-py (unittest.mock)
  driver: pytest
  format_note: Reuse the existing _make_mock_nc() harness and
    patch('nats_core.client.nats.connect'); assert mock_nc.publish.call_args for
    subject / raw body / headers['Nats-Msg-Id'].
---

# Task: Unit test suite — MemoryEpisodeV1, publish_episode, make_memory_episode factory

## Description

Cover the schema and the publisher with **unit** tests, mapping the seed ACs onto
this repo's real patterns. There is **no `TestNatsBroker`** here — unit tests
simulate nats-py with `AsyncMock` (`_make_mock_nc()` + `patch("nats_core.client.nats.connect")`),
and `conftest.py` uses **factory functions**, not stateful fixtures.

## Scope

### `tests/conftest.py`

Add a `make_memory_episode(**overrides)` factory returning a valid
`MemoryEpisodeV1` with sensible defaults, able to build a body just over / under
`MAX_EPISODE_BODY_BYTES` via a `body=` override (e.g. `body="x" * n`).

### `tests/test_memory_episode.py` (new)

Schema tests (mark `@pytest.mark.unit`; add `smoke`/`boundary`/`negative` where apt):

- All required fields present; optionals default to `None`.
- `group_id` is absent from `model_fields`.
- `extra="ignore"`: `model_validate_json` of a payload with an unknown key drops it.
- `episode_type` with a dot / space / `>` / `*` is rejected at construction (`negative`).

### `tests/test_client.py`

`publish_episode` tests (reuse `_make_mock_nc()` + `patch("nats_core.client.nats.connect")`):

- **Happy path** (`smoke`): `mock_nc.publish` called exactly once; positional
  `subject == "memory.episode.{project_id}.{episode_type}"` (resolved); the body
  arg re-parses via `MemoryEpisodeV1.model_validate_json` (**raw**, not envelope-wrapped);
  `call_args.kwargs["headers"]["Nats-Msg-Id"] == episode.episode_id`.
- **Oversized** (`boundary`/`negative`): an episode whose serialized form exceeds
  `MAX_EPISODE_BODY_BYTES` makes `publish_episode` raise `ValueError` (message contains
  the measured size and the limit) and `mock_nc.publish` is **not** called. A sibling
  just under the limit publishes once.
- **Not connected** (`negative`): `publish_episode` on a fresh (un-connected) client raises `RuntimeError`.

## Acceptance Criteria

- [ ] `tests/conftest.py` has `make_memory_episode(**overrides) -> MemoryEpisodeV1`
      (factory function, no stateful fixture) with defaults, supporting a `body=` override
      large enough to cross `MAX_EPISODE_BODY_BYTES`.
- [ ] `tests/test_memory_episode.py` covers: required/optional fields, `group_id` absent,
      `extra="ignore"` drops unknowns, and `episode_type` dot/space/wildcard rejected at construction.
- [ ] Happy-path `publish_episode` test asserts the single `mock_nc.publish` call's
      resolved subject, **raw** re-parseable body, and `headers["Nats-Msg-Id"] == episode_id`.
- [ ] Oversized-body test asserts `ValueError` (with measured size + limit in the message)
      and that `mock_nc.publish` was **not** called; under-limit sibling publishes once.
- [ ] `publish_episode` on a not-connected client raises `RuntimeError`.
- [ ] All new tests pass under the default gate (`pytest -m 'not integration'`); ≥ 80% line /
      75% branch coverage on the new schema + helper code.

## Implementation Notes

- Build oversized bodies from the constant: `body="x" * (MAX_EPISODE_BODY_BYTES + 1)` then
  account for JSON overhead — assert on the helper's behaviour, not an exact byte count.
- Assert headers via `mock_nc.publish.call_args.kwargs["headers"]` (the helper passes `headers=` as kwarg).
- Follow `test_<unit>_<scenario>_<expected>` naming.

## Coach Validation Commands

```bash
pytest tests/test_memory_episode.py tests/test_client.py -q -m "not integration"
pytest tests/ -q -m "not integration"
ruff check tests/test_memory_episode.py tests/test_client.py tests/conftest.py
```


---

> **Tracker reconcile 2026-07-11 (WS3-S8 sweep).** FEAT-MEP1 shipped and merged at nats-core `d1f421e` (Merge FEAT-MEP1: Memory Episode Publisher, 2026-06-24); code landed in `src/nats_core/events/_memory.py` + `topics.py`. Status flipped `->` completed and file relocated to `tasks/completed/memory-episode-publisher/` to match the completed feature YAML rollup (`.guardkit/features/FEAT-MEP1.yaml` status=completed, this task status=completed). No content change.
