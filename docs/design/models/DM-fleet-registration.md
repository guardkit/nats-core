# Data Model: Fleet Registration

**Design Unit:** Fleet Registration (manifest.py, events/fleet.py)
**Date:** 2026-04-07

---

## Entity: AgentManifest

The single source of truth for an agent's capabilities. Published directly to
`fleet.register`. Stored in NATS KV. MCP tools derived from this.

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `agent_id` | `str` | (required) | Unique in registry | Agent identifier |
| `name` | `str` | (required) | | Human-readable name |
| `version` | `str` | `"0.1.0"` | Semver | Agent software version |
| `intents` | `list[IntentCapability]` | `[]` | | Jarvis routing capabilities |
| `tools` | `list[ToolCapability]` | `[]` | | Direct invocation operations |
| `template` | `str` | (required) | | Agent template name |
| `max_concurrent` | `int` | `1` | `ge=1` | Max parallel tasks |
| `status` | `Literal` | `"ready"` | ready/starting/degraded | Current status |
| `trust_tier` | `Literal` | `"specialist"` | core/specialist/extension | Trust level |
| `required_permissions` | `list[str]` | `[]` | | Required permissions |
| `container_id` | `str \| None` | `None` | | Docker container ID |
| `metadata` | `dict[str, str]` | `{}` | | Extensible metadata |

---

## Entity: IntentCapability

Describes a single intent an agent can handle. Used by Jarvis for routing.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `pattern` | `str` | Non-empty | Intent pattern (e.g., "software.build") |
| `signals` | `list[str]` | | Signal words for intent matching |
| `confidence` | `float` | `ge=0.0, le=1.0` | How well agent handles this intent |
| `description` | `str` | | Human-readable description |

---

## Entity: ToolCapability

A specific operation an agent exposes for direct invocation.

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `name` | `str` | (required) | Non-empty | Tool name |
| `description` | `str` | (required) | | Human/model-readable description |
| `parameters` | `dict[str, Any]` | (required) | Valid JSON Schema | Input schema |
| `returns` | `str` | (required) | | Return value description |
| `risk_level` | `Literal` | `"read_only"` | read_only/mutating/destructive | Risk classification |
| `async_mode` | `bool` | `False` | | True if long-running |
| `requires_approval` | `bool` | `False` | | True if human-in-the-loop needed |

---

## Entity: AgentHeartbeatPayload

Lightweight periodic liveness signal.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_id` | `str` | (required) | Agent identifier |
| `status` | `Literal` | (required) | ready/busy/degraded/draining |
| `queue_depth` | `int` | `0` | Pending tasks |
| `active_tasks` | `int` | `0` | Currently executing |
| `uptime_seconds` | `int` | (required) | Agent uptime |
| `last_task_completed_at` | `datetime \| None` | `None` | Last completion time |
| `active_workflow_states` | `dict[str, str]` | `{}` | task_id -> state mapping |

---

## Entity: AgentDeregistrationPayload

Minimal graceful shutdown signal.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent_id` | `str` | (required) | Agent identifier |
| `reason` | `str` | `"shutdown"` | shutdown/maintenance/error |

---

## Entity: ManifestRegistry (ABC)

Abstract interface for agent manifest storage.

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `register` | `manifest: AgentManifest` | `None` | Store manifest |
| `deregister` | `agent_id: str` | `None` | Remove manifest |
| `get` | `agent_id: str` | `AgentManifest \| None` | Retrieve by ID |
| `list_all` | | `list[AgentManifest]` | All registered |
| `find_by_intent` | `intent: str` | `list[AgentManifest]` | Filter by intent |
| `find_by_tool` | `tool_name: str` | `list[AgentManifest]` | Filter by tool |

**Implementations:**
- `NATSKVManifestRegistry` -- NATS KV `agent-registry` bucket (production)
- `InMemoryManifestRegistry` -- dict-backed (testing)

---

## Relationships

```
AgentManifest
  |-- declares --> IntentCapability[] (routing)
  |-- exposes  --> ToolCapability[] (direct invocation)
  |-- stored in --> ManifestRegistry (KV or in-memory)
  |-- published to --> fleet.register (NATS topic)

AgentHeartbeatPayload
  |-- references --> AgentManifest.agent_id
  |-- published to --> fleet.heartbeat.{agent_id}
  |-- monitored by --> Jarvis Router (timeout 90s)

AgentDeregistrationPayload
  |-- references --> AgentManifest.agent_id
  |-- triggers --> ManifestRegistry.deregister()
```

---

## Invariants

1. `agent_id` must be unique in the registry
2. `confidence` constrained to 0.0-1.0
3. `ToolCapability.parameters` must be valid JSON Schema
4. Heartbeat timeout: 90s without heartbeat -> agent marked unavailable
5. `ManifestRegistry.register()` upserts -- re-registration replaces previous entry
