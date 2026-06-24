---
id: TASK-MEP-005
title: Optional live @integration round-trip echo on GB10 (memory subject)
status: backlog
created: 2026-06-24 00:00:00+00:00
updated: '2026-06-24T00:00:00+00:00'
priority: medium
task_type: testing
tags:
- memory-publisher
- integration
- nats-live
- optional
complexity: 3
wave: 3
implementation_mode: direct
parent_review: TASK-REV-MEP1
feature_id: FEAT-MEP1
dependencies:
- TASK-MEP-001
- TASK-MEP-003
consumer_context:
- task: TASK-MEP-003
  consumes: NATSClient.publish_episode
  framework: live nats-py connection to GB10 (core NATS, no JetStream)
  driver: nats-py
  format_note: Publish via a connected NATSClient.publish_episode() and self-subscribe
    on memory.episode.{project_id}.{episode_type}; decode the raw body with
    nats-core's OWN MemoryEpisodeV1. Do NOT assert JetStream dedupe (needs P2 stream).
---

# Task: Optional live @integration round-trip echo on GB10 (memory subject)

## Description

**Optional** for P1 acceptance — the `AsyncMock` unit round-trip (TASK-MEP-004) is
the primary gate. This adds a live core-NATS publish/subscribe **echo** proving the
real wire path: a connected `NATSClient.publish_episode()` emits the raw body +
`Nats-Msg-Id` header, and a self-subscriber decodes it back with nats-core's **own**
`MemoryEpisodeV1`. It is skipped by default (`addopts = "-m 'not integration'"`).

## Scope

### `tests/integration/test_memory_episode_live.py` (new)

- File name follows the established `*_live.py` convention (cf. `test_pipeline_payloads_live.py`).
- Mark every test `@pytest.mark.integration` so the default gate skips it.
- Do a **core-NATS** publish → self-subscribe echo on
  `memory.episode.{project_id}.{episode_type}` — its **own** subscription/setup.
  Do **not** reuse the integration `conftest.py` `PIPELINE_TEST` stream/subjects
  (it only covers `pipeline.>`), and do **not** require the `MEMORY` JetStream
  stream (that is P2).
- The subscriber decodes `MemoryEpisodeV1.model_validate_json(msg.data)`, asserts the
  round-tripped fields match, and asserts the received message's `Nats-Msg-Id`
  header equals `episode_id`.

## Acceptance Criteria

- [ ] `tests/integration/test_memory_episode_live.py` exists, every test marked
      `@pytest.mark.integration`, and the suite is skipped under the default
      `pytest -m 'not integration'` gate.
- [ ] The test publishes via a connected `NATSClient.publish_episode()` and self-subscribes
      on the resolved `memory.episode.{project_id}.{episode_type}` subject (core NATS, no stream).
- [ ] The subscriber decodes the raw body with `MemoryEpisodeV1.model_validate_json` and asserts
      field equality; the received `Nats-Msg-Id` header equals `episode_id`.
- [ ] The test does **not** assert JetStream server-side dedupe and does **not** point at the
      pre-P3 `fleet-memory` relay; a docstring records the `project → project_id` sequencing caveat
      and that dedupe verification is deferred to P3.

## Implementation Notes

- Connection + credential loading mirrors `tests/integration/conftest.py` (`RICH_NATS_PASSWORD`,
  GB10 `nats://100.84.90.91:4222`); `pytest.skip` when the password/VPN is unavailable.
- A core-NATS subscribe→publish→await echo (no stream) is sufficient to prove body+header transit.
- Keep it self-contained; if you add a fixture, prefer a module-scoped async connection like the
  existing integration conftest, but with a memory-specific subject.

## Coach Validation Commands

```bash
pytest tests/integration/test_memory_episode_live.py -q -m integration -k memory  # requires GB10 + RICH_NATS_PASSWORD
pytest tests/ -q -m "not integration"   # confirm it is correctly skipped by default
ruff check tests/integration/test_memory_episode_live.py
```
