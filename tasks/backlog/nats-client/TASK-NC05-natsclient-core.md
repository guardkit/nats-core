---
id: TASK-NC05
title: NATSClient core (connect / publish / subscribe)
status: in_review
created: 2026-04-08 00:00:00+00:00
updated: 2026-04-08 00:00:00+00:00
priority: high
task_type: feature
tags:
- nats-client
- core
- async
- pub-sub
- connection
complexity: 6
wave: 4
implementation_mode: task-work
parent_review: TASK-1T1W
feature_id: FEAT-1T1W
dependencies:
- TASK-NC01
- TASK-NC02
- TASK-ME02
consumer_context:
- task: TASK-NC01
  consumes: NATSConfig
  framework: pydantic-settings (nats_core.config.NATSConfig)
  driver: pydantic-settings
  format_note: NATSClient.__init__ receives NATSConfig; nats-py connection uses config.url,
    config.connect_timeout, config.max_reconnect_attempts, config.reconnect_time_wait,
    config.name, config.user, config.password, config.creds_file
- task: TASK-NC02
  consumes: Topics
  framework: Python class (nats_core.topics.Topics)
  driver: pure python
  format_note: publish() receives a pre-resolved topic string; Topics.resolve() must
    be called by the caller or in publish() for validation; Topics.for_project() applies
    project prefix when project arg is given
- task: TASK-ME02
  consumes: MessageEnvelope
  framework: Pydantic BaseModel (nats_core.envelope.MessageEnvelope)
  driver: pydantic
  format_note: publish() auto-constructs MessageEnvelope(message_id=uuid4(), timestamp=utcnow(),
    version='1.0', source_id=source_id, event_type=event_type, project=project, correlation_id=correlation_id,
    payload=payload.model_dump()); subscribe() callback receives MessageEnvelope.model_validate_json(raw)
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-3845
  base_branch: main
  started_at: '2026-04-08T21:51:19.080702'
  last_updated: '2026-04-08T21:56:45.614856'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T21:51:19.080702'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: NATSClient core (connect / publish / subscribe)

## Description

Implement the `NATSClient` class in `src/nats_core/client.py` covering the connection
lifecycle, typed publish, and typed subscribe. Fleet convenience methods and
`call_agent_tool` are added in TASK-NC06 and TASK-NC07 respectively.

## Scope

### Class: `NATSClient`

```python
class NATSClient:
    def __init__(self, config: NATSConfig) -> None: ...
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def publish(
        self,
        topic: str,
        payload: BaseModel,
        event_type: EventType,
        source_id: str,
        project: str | None = None,
        correlation_id: str | None = None,
    ) -> None: ...
    async def subscribe(
        self,
        topic: str,
        callback: Callable[[MessageEnvelope], Awaitable[None]],
    ) -> Subscription: ...
```

### Connection lifecycle

- `connect()` uses `nats.connect()` with retry and exponential backoff configured
  via `NATSConfig` fields (`max_reconnect_attempts`, `reconnect_time_wait`,
  `connect_timeout`)
- `connect()` on an already-connected client must raise `RuntimeError` or be safely
  idempotent (no duplicate underlying connections)
- `disconnect()` calls `nc.drain()` then `nc.close()` to drain all active subscriptions
  before closing
- Internal `_nc: nats.aio.client.Client | None` attribute — `None` when disconnected

### publish()

1. Raise `RuntimeError("client is not connected")` if `_nc is None`
2. Validate `topic` has no leading/trailing whitespace; raise `ValueError` if not clean
3. Apply `Topics.for_project(project, topic)` if `project` is provided
4. Construct `MessageEnvelope`:
   - `message_id`: `str(uuid.uuid4())`
   - `timestamp`: `datetime.now(timezone.utc).isoformat()`
   - `version`: `"1.0"`
   - `source_id`: from arg
   - `event_type`: from arg
   - `project`: from arg
   - `correlation_id`: from arg
   - `payload`: `payload.model_dump()`
5. Publish `envelope.model_dump_json().encode()` to topic via `_nc.publish()`

### subscribe()

1. Raise `RuntimeError("client is not connected")` if `_nc is None`
2. Subscribe via `_nc.subscribe(topic, cb=_internal_callback)`
3. Internal callback:
   - Parse raw bytes as `MessageEnvelope.model_validate_json()`
   - On `ValidationError` or `JSONDecodeError`: log error to stderr, do NOT raise
   - On success: `await callback(envelope)`
4. Return the `Subscription` object

## Acceptance Criteria

- [ ] `await client.connect()` establishes connection to NATS (test with nats-server or mock)
- [ ] `client.publish()` before `connect()` raises `RuntimeError` with "not connected" in message
- [ ] `client.subscribe()` before `connect()` raises `RuntimeError` with "not connected" in message
- [ ] Published message arrives as valid JSON-serialised `MessageEnvelope`
- [ ] `envelope.source_id` matches the `source_id` arg
- [ ] `envelope.event_type` matches the `event_type` arg
- [ ] `envelope.message_id` is a valid UUID v4 string
- [ ] `envelope.timestamp` is within 1 second of now in UTC
- [ ] `envelope.version` == `"1.0"`
- [ ] `envelope.payload` contains the serialised payload fields
- [ ] Project arg prefixes topic: `project="finproxy"` → topic `"finproxy.pipeline.build-complete.FEAT-001"`
- [ ] `correlation_id` arg is present in envelope
- [ ] `disconnect()` drains all subscriptions before close (no message loss mid-drain)
- [ ] Received invalid JSON does not crash subscriber — error logged to stderr
- [ ] `NATSClient` with `source_id=""` raises validation error at creation (validate in `__init__`)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

```python
"""Seam tests: verify NATSConfig and Topics contracts as consumed by NATSClient."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("NATSConfig")
def test_nats_config_fields_match_nats_py_connect_signature():
    """Verify NATSConfig fields can be passed to nats.connect() without TypeError.

    Contract: config.url, connect_timeout, max_reconnect_attempts, reconnect_time_wait
    must all exist as the correct types expected by nats-py.
    Producer: TASK-NC01
    """
    from nats_core.config import NATSConfig

    config = NATSConfig()
    assert isinstance(config.url, str)
    assert config.url.startswith("nats://")
    assert isinstance(config.connect_timeout, float)
    assert isinstance(config.max_reconnect_attempts, int)
    assert isinstance(config.reconnect_time_wait, float)


@pytest.mark.seam
@pytest.mark.integration_contract("Topics")
def test_topics_resolve_returns_str_without_placeholders():
    """Verify Topics.resolve() returns a fully-resolved string (no curly braces).

    Contract: publish() receives pre-resolved topic string; Topics.resolve() must
    return str with no remaining {placeholder} tokens.
    Producer: TASK-NC02
    """
    from nats_core.topics import Topics

    resolved = Topics.resolve(Topics.Pipeline.BUILD_COMPLETE, feature_id="FEAT-001")
    assert isinstance(resolved, str)
    assert "{" not in resolved
    assert resolved == "pipeline.build-complete.FEAT-001"


@pytest.mark.seam
@pytest.mark.integration_contract("MessageEnvelope")
def test_message_envelope_json_round_trips():
    """Verify MessageEnvelope.model_dump_json() / model_validate_json() round-trips.

    Contract: publish() encodes envelope as JSON bytes; subscribe() decodes with
    model_validate_json(). Format must be lossless.
    Producer: TASK-ME02
    """
    from nats_core.envelope import MessageEnvelope, EventType

    env = MessageEnvelope(
        message_id="550e8400-e29b-41d4-a716-446655440000",
        timestamp="2026-04-08T00:00:00Z",
        version="1.0",
        source_id="test-agent",
        event_type=EventType.BUILD_COMPLETE,
        payload={"feature_id": "FEAT-001"},
    )
    raw = env.model_dump_json()
    restored = MessageEnvelope.model_validate_json(raw)
    assert restored.source_id == "test-agent"
    assert restored.event_type == EventType.BUILD_COMPLETE
```

## Implementation Notes

- Import `nats` (nats-py) — `import nats`; connection via `await nats.connect(...)`
- Use `asyncio` for async — no threading
- `_nc` is private; expose no internal nats-py types in the public API
- Error handling in subscriber callback: `import logging; logger = logging.getLogger(__name__)` — use `logger.error()`, never `print()`
- `source_id` validation in `__init__`: raise `ValueError` if empty string

## Coach Validation Commands

```bash
python -c "from nats_core.client import NATSClient; from nats_core.config import NATSConfig; c = NATSClient(NATSConfig()); print('OK')"
python -c "from nats_core.client import NATSClient; from nats_core.config import NATSConfig; NATSClient(NATSConfig(), source_id='')" 2>&1 | grep -i "error\|ValueError"
ruff check src/nats_core/client.py
mypy src/nats_core/client.py
```
