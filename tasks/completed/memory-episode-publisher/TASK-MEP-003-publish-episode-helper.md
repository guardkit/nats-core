---
complexity: 5
consumer_context:
- consumes: MemoryEpisodeV1
  driver: pydantic
  format_note: Publish the RAW model JSON (model_dump_json().encode()) as the NATS
    message body — NO MessageEnvelope wrapping. The fleet-memory relay decodes the
    body directly via MemoryEpisodeV1.model_validate_json(msg.data).
  framework: Pydantic BaseModel (nats_core.events._memory)
  task: TASK-MEP-001
- consumes: MAX_EPISODE_BODY_BYTES
  driver: stdlib
  format_note: Measure len(episode.model_dump_json().encode()) (FULL encoded wire
    bytes, not the body field alone); reject with ValueError if it exceeds the limit.
  framework: int module constant (nats_core.events._memory)
  task: TASK-MEP-001
- consumes: Topics.Memory.EPISODE
  driver: nats_core
  format_note: Build the subject via Topics.resolve(Topics.Memory.EPISODE, project_id=...,
    episode_type=...) — never Topics.for_project (project_id is already the first
    segment).
  framework: Topics registry template (nats_core.topics)
  task: TASK-MEP-002
created: 2026-06-24 00:00:00+00:00
dependencies:
- TASK-MEP-001
- TASK-MEP-002
feature_id: FEAT-MEP1
id: TASK-MEP-003
implementation_mode: task-work
parent_review: TASK-REV-MEP1
priority: high
status: completed
completed: '2026-06-24T00:00:00+00:00'
tags:
- memory-publisher
- nats-client
- publish
- jetstream-dedupe
task_type: feature
title: NATSClient.publish_episode() — raw publish, Nats-Msg-Id header, 900KB reject
  guard
updated: '2026-06-24T00:00:00+00:00'
wave: 2
---

# Task: NATSClient.publish_episode() — raw publish, Nats-Msg-Id header, 900KB reject guard

## Description

Add `NATSClient.publish_episode(episode)` — the framework-neutral helper that
publishes a `MemoryEpisodeV1` onto `memory.episode.{project_id}.{episode_type}`.
It is a **method on `NATSClient`** (not a free function or wrapper class) because
only `NATSClient` legitimately owns the private `self._nc`, and `nc.publish` is the
only call that can attach the `Nats-Msg-Id` header. This mirrors the existing
`register_agent` / `deregister_agent` / `heartbeat` methods.

Two hard requirements drive the design:

1. **Bypass `MessageEnvelope`** — the relay reads the raw `MemoryEpisodeV1` JSON as
   the message body, so the helper must publish `episode.model_dump_json().encode()`
   directly (it must **not** call `publish()`, which wraps in an envelope).
2. **Set the dedupe header** — `headers={"Nats-Msg-Id": episode.episode_id}` so
   JetStream performs server-side dedupe (one `episode_id` == one stored message).

## Scope

### `src/nats_core/client.py`

```python
from nats_core.events import MAX_EPISODE_BODY_BYTES, MemoryEpisodeV1

async def publish_episode(self, episode: MemoryEpisodeV1) -> None:
    """Publish a memory episode (raw body + Nats-Msg-Id header, ≤900KB guard)."""
    if self._nc is None:
        msg = "client is not connected"
        raise RuntimeError(msg)

    data = episode.model_dump_json().encode()
    if len(data) > MAX_EPISODE_BODY_BYTES:
        msg = (
            f"memory episode body is {len(data)} bytes, exceeding the "
            f"{MAX_EPISODE_BODY_BYTES} byte (900KB) limit; chunk the content upstream"
        )
        raise ValueError(msg)

    subject = Topics.resolve(
        Topics.Memory.EPISODE,
        project_id=episode.project_id,
        episode_type=episode.episode_type,
    )
    await self._nc.publish(subject, data, headers={"Nats-Msg-Id": episode.episode_id})
```

- **Do not** widen `publish_raw(subject, data: bytes)` to take headers — keep the
  header-capable publish path private to this method. `publish_raw`'s request/reply
  contract and `publish()`'s envelope path are both untouched.
- Size policy is **reject-only** (no split, no DLQ). Splitting would mint multiple
  `episode_id`s per logical episode and break JetStream dedupe; the relay does its
  own heading-aware chunking downstream.
- The guard measures the **full encoded model** (the exact wire bytes), per the
  resolved planning decision — this is byte-identical to what NATS `max_payload` caps.

## Acceptance Criteria

- [ ] `NATSClient` has `async def publish_episode(self, episode: MemoryEpisodeV1) -> None`
      with a Google-style docstring; it raises `RuntimeError("client is not connected")`
      when `self._nc is None`.
- [ ] The method publishes the **raw** `episode.model_dump_json().encode()` (no
      `MessageEnvelope` constructed) via `self._nc.publish(subject, data, headers={"Nats-Msg-Id": episode.episode_id})`;
      the subject is built with `Topics.resolve(Topics.Memory.EPISODE, ...)` (no `for_project`).
- [ ] When `len(episode.model_dump_json().encode()) > MAX_EPISODE_BODY_BYTES`, the method
      raises `ValueError` whose message names the **measured byte size** and the 900KB limit,
      and `self._nc.publish` is **not** called.
- [ ] `publish_raw`'s `(subject, data: bytes)` signature is unchanged, and `publish()` is untouched.
- [ ] `MemoryEpisodeV1` / `MAX_EPISODE_BODY_BYTES` are imported into `client.py` from `nats_core.events`.
- [ ] All modified files pass project-configured lint/format checks (ruff + mypy strict) with zero errors.

## Seam Tests

The following seam tests validate the integration contracts this task consumes.
Implement them to verify the boundaries before integration.

```python
"""Seam test: verify MemoryEpisodeV1 wire contract from TASK-MEP-001."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("MemoryEpisodeV1")
def test_memory_episode_body_is_raw_not_enveloped():
    """The published body must be the raw MemoryEpisodeV1 JSON, re-parseable by the relay.

    Contract: RAW MemoryEpisodeV1 JSON as the wire body (NO MessageEnvelope wrapping).
    Producer: TASK-MEP-001 (schema) / TASK-MEP-003 (publish)
    """
    from nats_core import MemoryEpisodeV1

    episode = MemoryEpisodeV1(
        episode_id="e1", project_id="finproxy", episode_type="feature_outcome",
        content_format="markdown", body="hello",
    )
    data = episode.model_dump_json().encode()

    # The relay's consumption pattern: decode the body directly as MemoryEpisodeV1.
    round_tripped = MemoryEpisodeV1.model_validate_json(data)
    assert round_tripped.episode_id == "e1"
    # It must NOT look like a MessageEnvelope (no event_type/payload wrapper).
    import json
    assert "payload" not in json.loads(data)
```

```python
"""Seam test: verify Topics.Memory subject contract from TASK-MEP-002."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("Topics.Memory.EPISODE")
def test_memory_subject_resolves_to_partitioned_subject():
    """Subject must resolve to exactly memory.episode.{project_id}.{episode_type}.

    Contract: Topics.resolve(Topics.Memory.EPISODE, project_id, episode_type).
    Producer: TASK-MEP-002
    """
    from nats_core import Topics

    subject = Topics.resolve(
        Topics.Memory.EPISODE, project_id="finproxy", episode_type="feature_outcome"
    )
    assert subject == "memory.episode.finproxy.feature_outcome"
```

## Implementation Notes

- `nats.aio.client.Client.publish` signature: `publish(subject, payload=b'', reply='', headers=None)`.
- Keep the `msg = ...; raise ValueError(msg)` two-step form (ruff `EM101`/`TRY003` style used across this repo).
- This task does **not** verify server-side dedupe (that needs the P2 `MEMORY` stream).

## Coach Validation Commands

```bash
python -c "import inspect, nats_core.client as c; print('publish_episode' in dir(c.NATSClient))"
pytest tests/test_client.py -q -k "episode or publish_episode"
ruff check src/nats_core/client.py
mypy src/nats_core/client.py
```

---

> **Tracker reconcile 2026-07-11 (WS3-S8 sweep).** FEAT-MEP1 shipped and merged at nats-core `d1f421e` (Merge FEAT-MEP1: Memory Episode Publisher, 2026-06-24); code landed in `src/nats_core/events/_memory.py` + `topics.py`. Status flipped `->` completed and file relocated to `tasks/completed/memory-episode-publisher/` to match the completed feature YAML rollup (`.guardkit/features/FEAT-MEP1.yaml` status=completed, this task status=completed). No content change.
