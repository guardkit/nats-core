# API Contract: NATS Client & Config

**Bounded Context:** NATS Client & Config (client.py, config.py, agent_config.py)
**Protocols:** Python Public API
**Version:** 1.0.0
**Date:** 2026-04-07

---

## Python Public API

### NATSClient

```python
from nats_core.client import NATSClient

client = NATSClient(config=NATSConfig())
```

#### Lifecycle

```python
async def connect(self) -> None:
    """Connect to NATS server with retry and exponential backoff."""

async def disconnect(self) -> None:
    """Drain all subscriptions and close connection cleanly."""
```

#### Typed Publish

```python
async def publish(
    self,
    topic: str,
    payload: BaseModel,
    event_type: EventType,
    source_id: str,
    project: str | None = None,
    correlation_id: str | None = None,
) -> None:
    """Publish a typed event, automatically wrapping in MessageEnvelope.

    Args:
        topic: Resolved topic string (use Topics.resolve() first)
        payload: Pydantic model instance for the event payload
        event_type: Explicit EventType discriminator
        source_id: Originating service identifier
        project: Optional project scope for multi-tenancy
        correlation_id: Optional correlation ID for linking messages
    """
```

#### Typed Subscribe

```python
async def subscribe(
    self,
    topic: str,
    callback: Callable[[MessageEnvelope], Awaitable[None]],
) -> Subscription:
    """Subscribe to a topic with a typed callback.

    The callback receives a deserialised MessageEnvelope.
    """
```

#### Fleet Convenience Methods

```python
async def register_agent(self, manifest: AgentManifest) -> None:
    """Publish agent manifest to fleet.register and store in KV."""

async def deregister_agent(self, agent_id: str, reason: str = "shutdown") -> None:
    """Publish deregistration and remove from KV."""

async def heartbeat(self, heartbeat: AgentHeartbeatPayload) -> None:
    """Publish agent heartbeat to fleet.heartbeat.{agent_id}."""

async def get_fleet_registry(self) -> dict[str, AgentManifest]:
    """Read all registered agents from agent-registry KV bucket."""

async def watch_fleet(
    self,
    callback: Callable[[str, AgentManifest | None], Awaitable[None]],
) -> None:
    """Watch for fleet registration/deregistration/heartbeat events."""
```

#### Agent-to-Agent Tool Invocation

```python
async def call_agent_tool(
    self,
    agent_id: str,
    tool_name: str,
    params: dict[str, Any],
    timeout: float = 30.0,
) -> Any:
    """Invoke a tool on a remote agent via NATS request-reply.

    Publishes to agents.{agent_id}.tools.{tool_name} and awaits response.

    Args:
        agent_id: Target agent identifier
        tool_name: Tool name from the agent's manifest
        params: Tool parameters matching the tool's JSON Schema
        timeout: Request timeout in seconds

    Returns:
        Deserialised response from the target agent

    Raises:
        TimeoutError: If the agent does not respond within timeout
    """
```

---

### NATSKVManifestRegistry

```python
from nats_core.client import NATSKVManifestRegistry

registry = NATSKVManifestRegistry(client=nats_client, bucket="agent-registry")
```

Implements `ManifestRegistry` ABC backed by NATS JetStream KV store.

---

### NATSConfig

```python
from nats_core.config import NATSConfig
```

| Field | Type | Default | Env Var |
|-------|------|---------|---------|
| `url` | `str` | `"nats://localhost:4222"` | `NATS_URL` |
| `connect_timeout` | `float` | `5.0` | `NATS_CONNECT_TIMEOUT` |
| `reconnect_time_wait` | `float` | `2.0` | `NATS_RECONNECT_TIME_WAIT` |
| `max_reconnect_attempts` | `int` | `60` | `NATS_MAX_RECONNECT_ATTEMPTS` |
| `name` | `str` | `"nats-core-client"` | `NATS_NAME` |
| `user` | `str \| None` | `None` | `NATS_USER` |
| `password` | `str \| None` | `None` | `NATS_PASSWORD` |
| `creds_file` | `str \| None` | `None` | `NATS_CREDS_FILE` |

---

### AgentConfig

```python
from nats_core.agent_config import AgentConfig, ModelConfig, GraphitiConfig
```

**Module:** `agent_config.py` (separate from `config.py`)

| Field | Type | Default | Env Var Pattern |
|-------|------|---------|-----------------|
| `models` | `ModelConfig` | (required) | `AGENT_MODELS__*` |
| `graphiti` | `GraphitiConfig \| None` | `None` | `AGENT_GRAPHITI__*` |
| `nats` | `NATSConfig` | default NATSConfig | `AGENT_NATS__*` |
| `langsmith_project` | `str \| None` | `None` | `AGENT_LANGSMITH_PROJECT` |
| `heartbeat_interval_seconds` | `int` | `30` | `AGENT_HEARTBEAT_INTERVAL_SECONDS` |
| `heartbeat_timeout_seconds` | `int` | `90` | `AGENT_HEARTBEAT_TIMEOUT_SECONDS` |
| `max_task_timeout_seconds` | `int` | `600` | `AGENT_MAX_TASK_TIMEOUT_SECONDS` |

`env_prefix="AGENT_"`, `env_nested_delimiter="__"`

AgentConfig is LOCAL to each agent -- never published to fleet.register.

---

## Design Invariants

1. `NATSClient` wraps nats-py only -- no FastStream dependency (ADR-003)
2. All `publish()` calls auto-wrap in `MessageEnvelope`
3. `event_type` is always explicit on `publish()` -- no inference
4. `connect()` retries with exponential backoff on transient failures
5. `disconnect()` drains all subscriptions before closing
6. `call_agent_tool()` uses NATS request/reply with configurable timeout
7. `AgentConfig` never appears in `AgentManifest` -- private local config only
