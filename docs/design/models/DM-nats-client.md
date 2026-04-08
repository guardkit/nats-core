# Data Model: NATS Client & Config

**Design Unit:** NATS Client & Config (client.py, config.py, agent_config.py)
**Date:** 2026-04-07

---

## Entity: NATSClient

Typed pub/sub wrapper around nats-py. Not a data model per se, but the primary
interface consumers interact with.

### State Machine

```
Disconnected -> connect() -> Connected -> disconnect() -> Disconnected
                                |
                                +-> publish() / subscribe() / call_agent_tool()
                                +-> register_agent() / heartbeat() / watch_fleet()
```

### Dependencies

- `nats-py` (direct dependency -- ADR-003)
- `NATSConfig` (connection settings)
- `MessageEnvelope` (auto-wrapping)
- `Topics` (topic resolution)
- `ManifestRegistry` (fleet operations)

---

## Entity: NATSConfig

Connection settings loaded from environment.

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `url` | `str` | `"nats://localhost:4222"` | `NATS_URL` | Server URL |
| `connect_timeout` | `float` | `5.0` | `NATS_CONNECT_TIMEOUT` | Connection timeout (s) |
| `reconnect_time_wait` | `float` | `2.0` | `NATS_RECONNECT_TIME_WAIT` | Reconnect delay (s) |
| `max_reconnect_attempts` | `int` | `60` | `NATS_MAX_RECONNECT_ATTEMPTS` | Max reconnect tries |
| `name` | `str` | `"nats-core-client"` | `NATS_NAME` | Client name in NATS monitoring |
| `user` | `str \| None` | `None` | `NATS_USER` | Account user |
| `password` | `str \| None` | `None` | `NATS_PASSWORD` | Account password |
| `creds_file` | `str \| None` | `None` | `NATS_CREDS_FILE` | NKey credentials path |

**Base class:** `pydantic_settings.BaseSettings` with `env_prefix="NATS_"`

---

## Entity: AgentConfig

Fleet-wide runtime configuration schema. LOCAL to each agent -- never published.

**Module:** `agent_config.py` (separate from config.py)

| Field | Type | Default | Env Pattern | Description |
|-------|------|---------|-------------|-------------|
| `models` | `ModelConfig` | (required) | `AGENT_MODELS__*` | LLM endpoints |
| `graphiti` | `GraphitiConfig \| None` | `None` | `AGENT_GRAPHITI__*` | Knowledge graph |
| `nats` | `NATSConfig` | default | `AGENT_NATS__*` | NATS connection |
| `langsmith_project` | `str \| None` | `None` | `AGENT_LANGSMITH_PROJECT` | Tracing project |
| `langsmith_api_key` | `str \| None` | `None` | `AGENT_LANGSMITH_API_KEY` | Tracing key |
| `heartbeat_interval_seconds` | `int` | `30` | `AGENT_HEARTBEAT_INTERVAL_SECONDS` | Heartbeat interval |
| `heartbeat_timeout_seconds` | `int` | `90` | `AGENT_HEARTBEAT_TIMEOUT_SECONDS` | Liveness timeout |
| `max_task_timeout_seconds` | `int` | `600` | `AGENT_MAX_TASK_TIMEOUT_SECONDS` | Task timeout |
| `gemini_api_key` | `str \| None` | `None` | `AGENT_GEMINI_API_KEY` | |
| `anthropic_api_key` | `str \| None` | `None` | `AGENT_ANTHROPIC_API_KEY` | |
| `openai_api_key` | `str \| None` | `None` | `AGENT_OPENAI_API_KEY` | |

**Base class:** `pydantic_settings.BaseSettings` with `env_prefix="AGENT_"`, `env_nested_delimiter="__"`

---

## Entity: ModelConfig

LLM endpoint configuration nested in AgentConfig.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `reasoning_model` | `str` | (required) | Model for reasoning/orchestration |
| `reasoning_endpoint` | `str` | `""` | API endpoint (empty = provider default) |
| `implementation_model` | `str \| None` | `None` | Model for implementation tasks |
| `implementation_endpoint` | `str \| None` | `None` | Implementation endpoint |
| `embedding_model` | `str \| None` | `None` | Embedding model |
| `embedding_endpoint` | `str \| None` | `None` | Embedding endpoint |

---

## Entity: GraphitiConfig

Knowledge graph connection nested in AgentConfig.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `endpoint` | `str` | `"bolt://localhost:7687"` | FalkorDB bolt endpoint |
| `default_group_ids` | `list[str]` | `["appmilla-fleet"]` | Default query groups |

---

## Invariants

1. `NATSClient` wraps nats-py only -- no FastStream (ADR-003)
2. `AgentConfig` is never published to fleet.register
3. `NATSConfig` is a valid subset -- can be used standalone or nested in AgentConfig
4. API keys in `AgentConfig` are loaded from environment, never committed
5. `heartbeat_timeout_seconds` > `heartbeat_interval_seconds` (liveness detection logic)
