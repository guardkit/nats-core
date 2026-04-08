---
id: TASK-NC09
title: "Integration tests (NATSClient — all 33 BDD scenarios)"
status: pending
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
priority: high
task_type: testing
tags: [nats-client, integration-tests, pytest, bdd, natsclient]
complexity: 6
wave: 6
implementation_mode: task-work
parent_review: TASK-1T1W
feature_id: FEAT-1T1W
dependencies: [TASK-NC05, TASK-NC06, TASK-NC07]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Integration tests (NATSClient — all 33 BDD scenarios)

## Description

Write the integration test suite for `NATSClient` covering all 33 BDD scenarios from
`features/nats-client/nats-client.feature`. Tests require a running NATS server with
JetStream enabled.

## Scope

### Test file

```
tests/
    test_client_integration.py
    conftest.py                   (extend with NATS server fixture)
```

### conftest.py — NATS server fixture

```python
import pytest
import asyncio
import nats

@pytest.fixture
async def nats_client():
    """Connected NATSClient for integration tests."""
    from nats_core.client import NATSClient
    from nats_core.config import NATSConfig
    client = NATSClient(NATSConfig(url="nats://localhost:4222"))
    await client.connect()
    yield client
    await client.disconnect()
```

Mark all integration tests with `@pytest.mark.integration` so they can be excluded
when no NATS server is available.

### BDD scenario coverage

Group tests by BDD category. Each test corresponds to a named scenario:

**@key-example @smoke (6 scenarios):**
- `test_publish_typed_event_wraps_in_envelope` — BuildCompletePayload → envelope → topic
- `test_subscribe_receives_deserialised_envelope` — subscribe + publish → typed handler
- `test_project_scoped_publish_prefixes_topic` — project="finproxy" → prefixed topic
- `test_publish_with_correlation_id` — correlation_id in envelope, distinct message_id
- `test_register_agent_publishes_to_fleet_register` — register_agent → fleet.register
- `test_heartbeat_publishes_to_agent_specific_topic` — heartbeat → fleet.heartbeat.{id}
- `test_deregister_publishes_to_fleet_deregister` — deregister_agent → fleet.deregister
- `test_call_agent_tool_uses_request_reply` — call_agent_tool → request/reply

**@boundary (6 scenarios):**
- `test_publish_empty_payload_succeeds` — empty payload dict
- `test_single_char_source_id_publishes` — source_id="x"
- `test_empty_source_id_raises_validation_error` — source_id="" raises at creation
- `test_wildcard_subscription_receives_matching_messages` — pipeline.> captures multiple
- `test_deeply_nested_topic_resolves_correctly` — approval response topic
- `test_missing_topic_variable_raises_error` — KeyError on missing placeholder

**@negative (6 scenarios):**
- `test_publish_disconnected_raises` — RuntimeError before connect
- `test_subscribe_disconnected_raises` — RuntimeError before connect
- `test_invalid_json_does_not_crash_subscriber` — malformed bytes → error logged, no crash
- `test_unexpected_event_type_handled_gracefully` — wrong event_type → not crash
- `test_call_agent_tool_timeout` — offline agent → TimeoutError with agent_id in message
- `test_double_connect_raises_or_idempotent` — second connect() raises or safe

**@edge-case (13 scenarios):**
- `test_reconnect_after_transient_disconnection` — server restart → resubscriptions resume
- `test_graceful_disconnect_drains_subscriptions` — disconnect() → all msgs delivered
- `test_concurrent_publishes_no_corruption` — 50 concurrent publishes → all valid envelopes
- `test_multiple_handlers_same_topic` — two subscribers both receive message
- `test_get_fleet_registry_returns_all_agents` — 3 registrations → all in registry
- `test_watch_fleet_receives_events_in_order` — register then deregister → ordered callbacks
- `test_envelope_has_auto_generated_message_id_and_timestamp` — uuid4 + within 1s of now
- `test_payload_source_id_key_does_not_override_envelope` — security: payload key "source_id" stays in payload
- `test_wildcard_chars_in_segment_values_rejected` — agent_id="evil.>" → ValueError
- `test_concurrent_register_deregister_consistent_state` — concurrent KV ops → final state consistent
- `test_publish_during_reconnection_queues_or_fails_clearly` — reconnection window → queue or error
- `test_slow_consumer_backpressure_no_crash` — backpressure signal → no crash, warning logged
- `test_fleet_registry_unavailable_raises_error` — KV bucket down → RuntimeError

### Helper factory for integration tests

Add to `conftest.py`:

```python
def make_build_complete_payload(**overrides):
    from nats_core.events.pipeline import BuildCompletePayload
    defaults = {
        "feature_id": "FEAT-001",
        "build_id": "build-001",
        "repo": "test/repo",
        "branch": "main",
        "duration_seconds": 1.0,
        "tasks_completed": 1,
        "tasks_failed": 0,
        "tasks_total": 1,
        "summary": "done",
    }
    defaults.update(overrides)
    return BuildCompletePayload(**defaults)
```

## Acceptance Criteria

- [ ] All 33 BDD scenarios have corresponding tests
- [ ] All @smoke tests pass with a live NATS server + JetStream
- [ ] `test_invalid_json_does_not_crash_subscriber` verifies handler stays alive after malformed message
- [ ] `test_concurrent_publishes_no_corruption` uses `asyncio.gather()` with 50 tasks, verifies all 50 arrive
- [ ] `test_call_agent_tool_timeout` verifies `TimeoutError` raised with agent_id in message
- [ ] `test_envelope_has_auto_generated_message_id_and_timestamp` checks UUID v4 format and UTC within 1s
- [ ] All tests marked `@pytest.mark.integration` (excluded when `not integration`)
- [ ] @smoke tests additionally marked `@pytest.mark.smoke`
- [ ] Factory functions used — no stateful fixtures

## Implementation Notes

- Start a local NATS server with JetStream: `nats-server -js` (or Docker)
- For reconnection tests: use `asyncio.sleep()` to simulate disconnection window or monkeypatch
- For slow consumer test: may require mocking nats-py slow consumer error
- `asyncio_mode = "auto"` is set in pyproject.toml — all async tests run without explicit mark
- For `test_graceful_disconnect_drains_subscriptions`: publish messages, start drain, verify all arrive before disconnect completes

## Coach Validation Commands

```bash
# Run smoke tests only (fastest CI gate)
pytest tests/test_client_integration.py -v -m "smoke and integration"

# Run all integration tests
pytest tests/test_client_integration.py -v -m integration

# Full suite
pytest tests/ -v --cov=src/nats_core --cov-report=term-missing
```
