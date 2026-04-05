# Agent Manifest Contract — Shared Capability Declaration Schema

## For: All fleet agents, MCP adapters, and NATS infrastructure
## Date: 4 April 2026 (updated: 5 April 2026)
## Status: Draft — to be implemented in nats-core
## Owner: nats-core library (all repos depend on this)

---

## Purpose

The AgentManifest is the **single source of truth** for an agent's capabilities.
Both NATS fleet registration and MCP server tool definitions are derived from it.
This contract ensures that adding a new agent or adapter requires zero changes to
Jarvis router code, zero changes to other agents, and zero duplication of capability
definitions.

The **AgentConfig** is the companion schema for runtime configuration — how the
agent runs, not what it does. AgentConfig is local to each agent and never
published to the fleet.

Implementation target: `nats-core/src/nats_core/manifest.py` (AgentManifest)
and `nats-core/src/nats_core/config.py` (AgentConfig)

---

## Design Principles

1. **Metadata-first** — Define capabilities as data before code. A `list_tools()`
   call returns metadata without invoking anything.
2. **Two-level registry** — Intents (Jarvis routing) and Tools (direct interaction)
   are separate concerns in one manifest.
3. **Risk classification** — Every tool declares read_only, mutating, or destructive.
4. **Transport-agnostic** — Pure data. NATS publishes it. MCP translates it. Neither
   transport is privileged.
5. **Manifest vs Config separation** — Capabilities (what) are public and shared.
   Runtime settings (how) are private and local. API keys, endpoints, and timeouts
   never appear in the manifest.

Sources: Claude Code 12 Primitives analysis (Primitives #1, #2, #3, #15),
ADR-004 Dynamic Fleet Registration, Decisions DA2, DA15.

---

## Schema Definitions

### ToolCapability

```python
class ToolCapability(BaseModel):
    """A specific operation this agent exposes for direct invocation.

    Consumed by:
    - MCP adapters: each ToolCapability becomes an MCP tool definition
    - Agent-to-agent calls: targeted invocation via NATS tool topics
    - Jarvis: introspection of capabilities beyond intent routing
    """
    name: str                    # e.g. "run_architecture_session"
    description: str             # Human and model-readable
    parameters: dict[str, Any]   # JSON Schema for input
    returns: str                 # Return value description
    risk_level: Literal["read_only", "mutating", "destructive"] = "read_only"
    async_mode: bool = False     # True if long-running (returns run_id)
    requires_approval: bool = False  # True if human-in-the-loop needed
```

### IntentCapability

```python
class IntentCapability(BaseModel):
    """An intent this agent can handle, with confidence scoring.
    Used by Jarvis intent router. Unchanged from ADR-004."""
    pattern: str                 # e.g. "architecture.generate"
    signals: list[str]           # e.g. ["architect this", "C4 diagram"]
    confidence: float            # 0.0-1.0, Jarvis picks highest
    description: str             # Human-readable
```

### AgentManifest

```python
class AgentManifest(BaseModel):
    """Complete capability declaration for a fleet agent.

    Single source of truth. NATS registration and MCP tool
    definitions are both derived from this.

    This is the PUBLIC contract — published to fleet.register,
    readable by all fleet members. Never contains secrets,
    endpoints, or runtime configuration. See AgentConfig for those.
    """
    # Identity
    agent_id: str                # e.g. "architect-agent"
    name: str                    # e.g. "Architect Agent"
    version: str = "0.1.0"      # semver

    # Routing (Jarvis intent router)
    intents: list[IntentCapability] = []

    # Tools (MCP servers, agent-to-agent calls)
    tools: list[ToolCapability] = []

    # Operational
    template: str                # e.g. "weighted-evaluation"
    max_concurrent: int = 1
    status: Literal["ready", "starting", "degraded"] = "ready"

    # Trust and permissions
    trust_tier: Literal["core", "specialist", "extension"] = "specialist"
    required_permissions: list[str] = []
    # e.g. ["graphiti:read", "graphiti:write", "filesystem:read"]

    # Metadata
    container_id: str | None = None
    metadata: dict[str, str] = {}
```

### AgentHeartbeatPayload

```python
class AgentHeartbeatPayload(BaseModel):
    """Published periodically to fleet.heartbeat.{agent_id}."""
    agent_id: str
    status: Literal["ready", "busy", "degraded", "draining"]
    queue_depth: int = 0
    active_tasks: int = 0
    uptime_seconds: int
    last_task_completed_at: datetime | None = None
    active_workflow_states: dict[str, str] = {}
    # task_id → state: planned | executing | awaiting_approval | completed | failed
```

### AgentDeregistrationPayload

```python
class AgentDeregistrationPayload(BaseModel):
    """Published on graceful shutdown to fleet.deregister."""
    agent_id: str
    reason: str = "shutdown"  # shutdown | maintenance | error
```

---

## Companion Schema: AgentConfig (Runtime Configuration)

AgentConfig is the **private, local** counterpart to the public AgentManifest.
It defines HOW the agent runs — model endpoints, API keys, connection strings,
timeouts. It is never published to `fleet.register` and never shared with
other agents.

All agents import AgentConfig from nats-core so the schema is consistent
across the fleet. This prevents six agents drifting into six different config
formats, which would break fleet-level tooling (dashboards, cost tracking,
fleet compose environment injection).

Implementation target: `nats-core/src/nats_core/config.py`

### Schema

```python
from pydantic import Field
from pydantic_settings import BaseSettings


class ModelConfig(BaseModel):
    """Model endpoint configuration for an agent."""
    reasoning_model: str = Field(
        description="Model identifier for reasoning/orchestration, "
                    "e.g. 'gemini-3.1-pro', 'openai:gpt-4o', 'claude-sonnet-4-20250514'"
    )
    reasoning_endpoint: str = Field(
        default="",
        description="API endpoint URL. Empty string uses the provider's default."
    )
    implementation_model: str | None = Field(
        default=None,
        description="Model for implementation tasks (if two-model separation applies), "
                    "e.g. 'vllm:qwen3-coder-next'"
    )
    implementation_endpoint: str | None = Field(
        default=None,
        description="Implementation model endpoint, e.g. 'http://promaxgb10-41b1:8002/v1'"
    )
    embedding_model: str | None = Field(
        default=None,
        description="Embedding model if agent needs embeddings directly, "
                    "e.g. 'nomic-ai/nomic-embed-text-v1.5'"
    )
    embedding_endpoint: str | None = Field(
        default=None,
        description="Embedding endpoint, e.g. 'http://promaxgb10-41b1:8001/v1'"
    )


class GraphitiConfig(BaseModel):
    """Graphiti knowledge graph connection settings."""
    endpoint: str = Field(
        default="bolt://localhost:7687",
        description="FalkorDB/Neo4j bolt endpoint"
    )
    default_group_ids: list[str] = Field(
        default_factory=lambda: ["appmilla-fleet"],
        description="Default group IDs to query. Agents typically include "
                    "'appmilla-fleet' plus their project scope."
    )


class NATSConfig(BaseModel):
    """NATS connection settings."""
    url: str = Field(
        default="nats://localhost:4222",
        description="NATS server URL"
    )
    credentials_file: str | None = Field(
        default=None,
        description="Path to NATS credentials file"
    )


class AgentConfig(BaseSettings):
    """Runtime configuration for a fleet agent.

    LOCAL to each agent — never published to fleet.register.
    Loaded from agent-config.yaml, environment variables, or .env file.

    Uses pydantic-settings for environment variable override:
      AGENT_MODELS__REASONING_MODEL=gemini-3.1-pro
      AGENT_GRAPHITI__ENDPOINT=bolt://promaxgb10-41b1:7687
      AGENT_NATS__URL=nats://promaxgb10-41b1:4222
    """
    models: ModelConfig
    graphiti: GraphitiConfig | None = None
    nats: NATSConfig = Field(default_factory=NATSConfig)

    # Observability
    langsmith_project: str | None = Field(
        default=None,
        description="LangSmith project name for tracing. "
                    "Convention: '{agent_id}' or '{agent_id}-{project}'"
    )
    langsmith_api_key: str | None = None

    # Lifecycle
    heartbeat_interval_seconds: int = 30
    heartbeat_timeout_seconds: int = 90
    max_task_timeout_seconds: int = 600

    # API keys (loaded from environment)
    gemini_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    model_config = {"env_prefix": "AGENT_", "env_nested_delimiter": "__"}
```

### Per-Agent Config File

Each agent repo has an `agent-config.yaml.example` (committed) and
`agent-config.yaml` (gitignored, contains real credentials):

```yaml
# architect-agent/agent-config.yaml.example
models:
  reasoning_model: "gemini-3.1-pro"
  reasoning_endpoint: ""  # uses provider default
  implementation_model: null  # architect agent doesn't implement code
  embedding_model: "nomic-ai/nomic-embed-text-v1.5"
  embedding_endpoint: "http://promaxgb10-41b1:8001/v1"

graphiti:
  endpoint: "bolt://promaxgb10-41b1:7687"
  default_group_ids:
    - "appmilla-fleet"
    # Add project scope when running: e.g. "finproxy"

nats:
  url: "nats://promaxgb10-41b1:4222"

langsmith_project: "architect-agent"
heartbeat_interval_seconds: 30
max_task_timeout_seconds: 1200  # 20 min — architecture sessions are longer
```

### Why Both Schemas Live in nats-core

Both `AgentManifest` and `AgentConfig` are imported by every agent. Defining
them in nats-core ensures:
- One Pydantic model, not six drift-prone variants
- Fleet-level tooling (dashboard, cost tracking) knows the config shape
- Docker Compose fleet environment variables map to a known schema
- New agents get config validation for free by importing the base class

---

## Topic Structure

```python
class Topics:
    class Fleet:
        REGISTER = "fleet.register"
        DEREGISTER = "fleet.deregister"
        HEARTBEAT = "fleet.heartbeat.{agent_id}"
        HEARTBEAT_ALL = "fleet.heartbeat.>"

    class Agents:
        """Direct agent-to-agent tool invocation."""
        TOOLS = "agents.{agent_id}.tools.{tool_name}"
        TOOLS_ALL = "agents.{agent_id}.tools.>"
        RESULT = "agents.{agent_id}.result.{request_id}"
```

---

## Transport Derivation

### NATS (fleet production)
```python
manifest = get_architect_agent_manifest()
await client.register_agent(manifest)      # publishes to fleet.register
for tool in manifest.tools:
    await client.subscribe(
        f"agents.{manifest.agent_id}.tools.{tool.name}", handle_tool_call
    )
```

### MCP (Claude Desktop adapter)
```python
manifest = get_architect_agent_manifest()
for tool in manifest.tools:
    @server.tool(name=f"architect:{tool.name}", description=tool.description)
    async def handle(params, _tool=tool):
        return await invoke_agent_tool(_tool.name, params)
```

### Direct import (testing)
```python
from architect_agent import run_architecture_session
result = await run_architecture_session(docs_path="...", scope="...")
```

---

## Registry Interface

```python
class ManifestRegistry(ABC):
    """Abstract registry backed by NATS KV, in-memory, or file."""
    async def register(self, manifest: AgentManifest) -> None: ...
    async def deregister(self, agent_id: str) -> None: ...
    async def get(self, agent_id: str) -> AgentManifest | None: ...
    async def list_all(self) -> list[AgentManifest]: ...
    async def find_by_intent(self, intent: str) -> list[AgentManifest]: ...
    async def find_by_tool(self, tool_name: str) -> list[AgentManifest]: ...
```

---

## Supersedes

- `AgentRegistrationPayload` in fleet registration addendum (absorbed into AgentManifest)

## Extends

- ADR-004: Dynamic Fleet Registration (adds tool-level registry)
- ADR-005: Two-Level Capability Registry (to be created)

---

*Created: 4 April 2026 | Agent manifest contract design session*
*Updated: 5 April 2026 | Added AgentConfig companion schema (DA15)*
