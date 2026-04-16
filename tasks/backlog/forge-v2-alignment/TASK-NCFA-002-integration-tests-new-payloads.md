---
id: TASK-NCFA-002
title: Integration tests for new pipeline payloads against live NATS on GB10
status: backlog
task_type: implementation
parent_review: forge/TASK-REV-A1F2
feature_id: FEAT-NCFA
priority: high
tags: [nats-core, integration-tests, forge-v2.2, jetstream]
complexity: 4
wave: 2
implementation_mode: task-work
dependencies: [TASK-NCFA-001]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Integration tests for new pipeline payloads against live NATS on GB10

## Context

TASK-NCFA-001 adds the payloads and topics. This task proves they round-trip cleanly through an actual JetStream instance on GB10 — envelope serialisation, stream persistence, consumer ack, deserialisation, forward-compat on extra fields.

## Prerequisites

- TASK-NCFA-001 merged
- `nats-infrastructure` running on GB10 with `PIPELINE` stream provisioned (already true per alignment review §2.2)
- Tailscale connectivity from the test runner

## Scope

### 1. Round-trip test per payload

In `tests/integration/test_pipeline_payloads_live.py` (new file), one test per new payload:

- `test_build_queued_round_trip_via_jetstream` — publish a `BuildQueuedPayload` wrapped in `MessageEnvelope` to `pipeline.build-queued.FEAT-TEST-001`, consume from `PIPELINE` stream, deserialise, assert field equality including `correlation_id`
- `test_build_paused_round_trip`
- `test_build_resumed_round_trip`
- `test_stage_complete_round_trip`
- `test_stage_gated_round_trip`

**Note (from TASK-7448 review):** The existing `tests/test_client_integration.py` uses `AsyncMock` to simulate nats-py — it does NOT connect to a live NATS server. There are no existing live NATS fixtures. This task must create new fixtures in `tests/integration/conftest.py`:
- `nats_client` — connects to GB10 via Tailscale, yields a connected `nats.aio.client.Client`, disconnects on teardown
- `jetstream_context` — creates a JetStream context from the live client

### 2. AckWait crash-recovery test

- `test_build_queued_unacked_redelivery` — publish a message, pull it but do not ack, wait for AckWait + 1s, pull again, assert the same message is redelivered. This is the test anchor §10 Phase 1 calls out as the validation signal.

### 3. Correlation ID threading test

- `test_correlation_id_threads_through_build_events` — publish a sequence: `BuildQueued` → `BuildStarted` → `BuildProgress` → `StageComplete` → `BuildComplete`, all with the same `correlation_id`. Subscribe to `pipeline.>`, filter by correlation_id, assert exactly those five events arrive in order.

### 4. Forward-compat test

- `test_build_queued_accepts_unknown_fields_from_future_publisher` — publish a payload with an extra `session_context` field that current nats-core does not know about; deserialise using the current Pydantic model; assert no exception and that the known fields parse correctly. Validates `ConfigDict(extra='allow')`.

### 5. Schema validation rejection test

- `test_build_queued_rejects_invalid_feature_id_over_nats` — publish a payload with `feature_id="bogus"`; consumer should receive the envelope, Pydantic should raise `ValidationError` on deserialisation. Assert the error path is surfaced cleanly (not swallowed).

### 6. Topic subscription pattern test

- `test_subscribe_all_pipeline_build_events_wildcard` — subscribe to `pipeline.build-*.>`, publish one of each build event, assert all arrive (exercises the `BUILD_QUEUED`, `BUILD_STARTED`, etc. subject pattern).

## Test environment

- Run against `nats-infrastructure` on GB10 via Tailscale (default test env)
- Tests must be marked `@pytest.mark.integration` so they are skipped in fast CI runs without live NATS
- Use short AckWait (e.g. 5s) in tests to keep them fast — the production default is 60m

## Acceptance criteria

- [ ] New test file `tests/integration/test_pipeline_payloads_live.py` exists with all seven tests
- [ ] `pytest -m integration tests/integration/test_pipeline_payloads_live.py` passes against a live NATS instance on GB10
- [ ] `test_build_queued_unacked_redelivery` demonstrably proves JetStream's AckWait redelivery
- [ ] Coverage for the new payloads is ≥98%

## Out of scope

- Load/stress testing (separate concern)
- Testing specialist-agent or Forge — those have their own integration suites
- Testing `NATSClient` internals — that is already covered at 98%
- Fixing any integration test flakiness unrelated to the new payloads
