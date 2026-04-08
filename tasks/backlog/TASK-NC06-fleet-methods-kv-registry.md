---
id: TASK-NC06
title: "Fleet convenience methods + NATSKVManifestRegistry"
status: pending
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
priority: high
task_type: feature
tags: [nats-client, fleet, kv, jetstream, registry]
complexity: 5
wave: 5
implementation_mode: task-work
parent_review: TASK-1T1W
feature_id: FEAT-1T1W
dependencies: [TASK-NC04, TASK-NC05]
consumer_context:
  - task: TASK-NC04
    consumes: AgentManifest
    framework: "Pydantic BaseModel (nats_core.manifest.AgentManifest)"
    driver: "pydantic"
    format_note: "register_agent() accepts AgentManifest; serialises to manifest.model_dump_json().encode() for fleet.register publish AND KV put; get_fleet_registry() returns dict[str, AgentManifest] by deserialising KV values with AgentManifest.model_validate_json()"
  - task: TASK-NC05
    consumes: NATSClient
    framework: "nats_core.client.NATSClient"
    driver: "nats-py"
    format_note: "Fleet methods are added directly to NATSClient class; NATSKVManifestRegistry receives a connected NATSClient instance; access JetStream via client._nc.jetstream()"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Fleet convenience methods + NATSKVManifestRegistry

## Description

Extend `NATSClient` in `src/nats_core/client.py` with fleet registration convenience
methods. Also implement `NATSKVManifestRegistry` — the NATS JetStream KV-backed
implementation of `ManifestRegistry`.

## Scope

### Fleet methods on `NATSClient`

```python
async def register_agent(self, manifest: AgentManifest) -> None:
    """Publish manifest to fleet.register AND store in agent-registry KV bucket."""

async def deregister_agent(self, agent_id: str, reason: str = "shutdown") -> None:
    """Publish AgentDeregistrationPayload to fleet.deregister AND delete from KV."""

async def heartbeat(self, heartbeat: AgentHeartbeatPayload) -> None:
    """Publish heartbeat to fleet.heartbeat.{agent_id}."""

async def get_fleet_registry(self) -> dict[str, AgentManifest]:
    """Read all registered agents from agent-registry KV bucket.
    Raises RuntimeError if KV bucket is unavailable."""

async def watch_fleet(
    self,
    callback: Callable[[str, AgentManifest | None], Awaitable[None]],
) -> None:
    """Watch agent-registry KV for put/delete events.
    Calls callback(agent_id, manifest_or_none) for each change."""
```

### Fleet method details

**`register_agent(manifest)`:**
1. Publish `manifest.model_dump_json().encode()` to `Topics.Fleet.REGISTER` with
   `event_type=EventType.AGENT_REGISTER`, `source_id=manifest.agent_id`
2. Also store in KV: `kv.put(manifest.agent_id, manifest.model_dump_json().encode())`

**`deregister_agent(agent_id, reason)`:**
1. Publish `AgentDeregistrationPayload(agent_id=agent_id, reason=reason)` to
   `Topics.Fleet.DEREGISTER` with `event_type=EventType.AGENT_DEREGISTER`,
   `source_id=agent_id`
2. Delete from KV: `kv.delete(agent_id)` (idempotent — ignore KeyNotFoundError)

**`heartbeat(heartbeat)`:**
1. Publish to `Topics.resolve(Topics.Fleet.HEARTBEAT, agent_id=heartbeat.agent_id)`
   with `event_type=EventType.AGENT_HEARTBEAT`, `source_id=heartbeat.agent_id`

**`get_fleet_registry()`:**
1. Get JetStream KV bucket `"agent-registry"`
2. Call `kv.keys()` to iterate; for each key call `kv.get(key)`
3. Deserialise each value with `AgentManifest.model_validate_json()`
4. Return `dict[str, AgentManifest]` keyed by `agent_id`
5. Raise `RuntimeError("registry unavailable")` if JetStream or bucket not accessible

**`watch_fleet(callback)`:**
1. Get KV bucket `"agent-registry"` and call `kv.watch(">")`
2. For each `KeyValue.Operation.PUT`: deserialise as `AgentManifest`, call `callback(key, manifest)`
3. For each `KeyValue.Operation.DEL` / `PURGE`: call `callback(key, None)`

### `NATSKVManifestRegistry`

```python
class NATSKVManifestRegistry(ManifestRegistry):
    def __init__(self, client: NATSClient, bucket: str = "agent-registry") -> None: ...
    async def register(self, manifest: AgentManifest) -> None: ...
    async def deregister(self, agent_id: str) -> None: ...
    async def get(self, agent_id: str) -> AgentManifest | None: ...
    async def list_all(self) -> list[AgentManifest]: ...
    async def find_by_intent(self, intent: str) -> list[AgentManifest]: ...
    async def find_by_tool(self, tool_name: str) -> list[AgentManifest]: ...
```

Delegates directly to NATS JetStream KV bucket operations. `find_by_intent` and
`find_by_tool` call `list_all()` then filter in-process.

## Acceptance Criteria

- [ ] `register_agent(manifest)` publishes to `fleet.register` topic
- [ ] `register_agent(manifest)` stores manifest in `agent-registry` KV bucket
- [ ] `deregister_agent("agent-x", "shutdown")` publishes to `fleet.deregister` with reason
- [ ] `heartbeat(payload)` publishes to `fleet.heartbeat.{agent_id}`
- [ ] `get_fleet_registry()` returns all 3 agents after 3 registrations
- [ ] `get_fleet_registry()` raises `RuntimeError` when KV bucket is unavailable
- [ ] `watch_fleet()` callback receives registration then deregistration events in order
- [ ] Simultaneous register+deregister for same agent leaves KV in a consistent final state
- [ ] `NATSKVManifestRegistry.get("unknown")` returns `None` (not raises)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Seam Tests

```python
"""Seam tests: verify AgentManifest and NATSClient contracts for fleet methods."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("AgentManifest")
def test_agent_manifest_serialises_to_bytes_for_kv():
    """Verify AgentManifest.model_dump_json().encode() produces valid UTF-8 bytes.

    Contract: register_agent() puts manifest.model_dump_json().encode() into KV;
    get_fleet_registry() reads bytes and calls AgentManifest.model_validate_json().
    Producer: TASK-NC04
    """
    from nats_core.manifest import AgentManifest

    manifest = AgentManifest(agent_id="test-agent", name="Test", template="basic")
    raw = manifest.model_dump_json().encode()
    assert isinstance(raw, bytes)
    restored = AgentManifest.model_validate_json(raw)
    assert restored.agent_id == "test-agent"


@pytest.mark.seam
@pytest.mark.integration_contract("NATSClient")
def test_nats_client_exposes_nc_after_connect():
    """Verify NATSClient._nc is non-None after connect() (required by fleet methods).

    Contract: fleet methods access JetStream via client._nc.jetstream(); this seam
    test verifies _nc is accessible (actual connection tested in integration tests).
    Producer: TASK-NC05
    """
    from nats_core.client import NATSClient
    from nats_core.config import NATSConfig

    client = NATSClient(NATSConfig())
    assert client._nc is None  # Not connected yet - correct initial state
    # Fleet methods must check _nc before accessing .jetstream()
```

## Implementation Notes

- JetStream KV via `_nc.jetstream()` → `js.key_value("agent-registry")`
- Create KV bucket if not exists: use `js.create_key_value(KeyValueConfig("agent-registry"))`
  or catch `BucketNotFoundError` and raise `RuntimeError`
- `watch_fleet` is a long-running coroutine — document that callers should `asyncio.create_task()` it
- `KV.Operation` enum: `PUT`, `DEL`, `PURGE` — handle all three in watch_fleet

## Coach Validation Commands

```bash
python -c "from nats_core.client import NATSClient, NATSKVManifestRegistry; print('OK')"
python -c "from nats_core.manifest import ManifestRegistry; from nats_core.client import NATSKVManifestRegistry; import inspect; print(inspect.isabstract(ManifestRegistry))"
ruff check src/nats_core/client.py
mypy src/nats_core/client.py
```
