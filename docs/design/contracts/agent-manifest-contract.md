# Agent Manifest Contract — Shared Capability Declaration Schema

## For: All fleet agents, MCP adapters, and NATS infrastructure
## Date: 4 April 2026
## Status: Draft — to be implemented in nats-core
## Owner: nats-core library (all repos depend on this)

---

## Purpose

The AgentManifest is the **single source of truth** for an agent's capabilities.
Both NATS fleet registration and MCP server tool definitions are derived from it.
This contract ensures that adding a new agent or adapter requires zero changes to
Jarvis router code, zero changes to other agents, and zero duplication of capability
definitions.

Implementation target: `nats-core/src/nats_core/manifest.py`

---

## Design Principles

1. **Metadata-first** — Define capabilities as data before code. A `list_tools()`
   call returns metadata without invoking anything.
2. **Two-level registry** — Intents (Jarvis routing) and Tools (direct interaction)
   are separate concerns in one manifest.
3. **Risk classification** — Every tool declares read_only, mutating, or destructive.
4. **Transport-agnostic** — Pure data. NATS publishes it. MCP translates it. Neither
   transport is privileged.

Sources: Claude Code 12 Primitives analysis (Primitives #1, #2, #3, #15),
ADR-004 Dynamic Fleet Registration, Decision DA2.

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
