# API Contract: Fleet Registration

**Bounded Context:** Fleet Registration (manifest.py, events/fleet.py)
**Protocols:** NATS Events, MCP Tool Definitions, Python Public API
**Version:** 1.0.0
**Date:** 2026-04-07

---

## Python Public API

### Manifest Models

```python
from nats_core.manifest import AgentManifest, IntentCapability, ToolCapability
from nats_core.manifest import ManifestRegistry, InMemoryManifestRegistry
from nats_core.client import NATSKVManifestRegistry
```

### AgentManifest

```python
class AgentManifest(BaseModel):
    """Complete capability declaration for a fleet agent.

    Single source of truth. Published directly to fleet.register.
    NATS KV stores this object. MCP tools derived from this.
    Never contains secrets or runtime configuration.
    """
    # Identity
    agent_id: str
    name: str
    version: str = "0.1.0"

    # Routing (Jarvis intent router)
    intents: list[IntentCapability] = []

    # Tools (MCP servers, agent-to-agent calls)
    tools: list[ToolCapability] = []

    # Operational
    template: str
    max_concurrent: int = 1
    status: Literal["ready", "starting", "degraded"] = "ready"

    # Trust and permissions
    trust_tier: Literal["core", "specialist", "extension"] = "specialist"
    required_permissions: list[str] = []

    # Metadata
    container_id: str | None = None
    metadata: dict[str, str] = {}
```

### IntentCapability

```python
class IntentCapability(BaseModel):
    """An intent this agent can handle, with confidence scoring."""
    pattern: str              # e.g., "software.build"
    signals: list[str]        # Signal words for intent matching
    confidence: float         # 0.0-1.0
    description: str
```

### ToolCapability

```python
class ToolCapability(BaseModel):
    """A specific operation this agent exposes for direct invocation."""
    name: str
    description: str
    parameters: dict[str, Any]      # JSON Schema for input
    returns: str
    risk_level: Literal["read_only", "mutating", "destructive"] = "read_only"
    async_mode: bool = False
    requires_approval: bool = False
```

### ManifestRegistry (ABC)

```python
class ManifestRegistry(ABC):
    """Abstract registry for agent manifests."""
    async def register(self, manifest: AgentManifest) -> None: ...
    async def deregister(self, agent_id: str) -> None: ...
    async def get(self, agent_id: str) -> AgentManifest | None: ...
    async def list_all(self) -> list[AgentManifest]: ...
    async def find_by_intent(self, intent: str) -> list[AgentManifest]: ...
    async def find_by_tool(self, tool_name: str) -> list[AgentManifest]: ...
```

**Implementations:**
- `NATSKVManifestRegistry` (in `client.py`) -- backed by NATS KV `agent-registry` bucket
- `InMemoryManifestRegistry` (in `manifest.py`) -- for testing

---

## NATS Event Contracts

### Registration Lifecycle

```
Agent starts  -> publishes AgentManifest to fleet.register
              -> Jarvis stores in agent-registry KV
              -> Agent begins heartbeating to fleet.heartbeat.{agent_id}

Agent running -> periodic heartbeat every 30s
              -> Jarvis watches fleet.heartbeat.> for timeout (90s)

Agent stops   -> publishes AgentDeregistrationPayload to fleet.deregister
              -> Jarvis removes from KV
```

### Request/Reply: Agent Tool Invocation

```
Caller -> publishes to agents.{agent_id}.tools.{tool_name}
       -> NATS request/reply pattern
       -> Target agent handles and replies
       -> Caller receives result (or timeout)
```

---

## MCP Tool Definitions

Each `ToolCapability` in an `AgentManifest` maps 1:1 to an MCP tool:

```json
{
  "name": "{agent_id}:{tool_name}",
  "description": "{tool_description}",
  "inputSchema": {
    "type": "object",
    "properties": { /* from ToolCapability.parameters */ }
  },
  "annotations": {
    "risk_level": "{read_only|mutating|destructive}",
    "requires_approval": false,
    "async_mode": false
  }
}
```

### MCP Adapter Pattern

```python
manifest = get_agent_manifest()
for tool in manifest.tools:
    @server.tool(
        name=f"{manifest.agent_id}:{tool.name}",
        description=tool.description,
    )
    async def handle(params, _tool=tool):
        return await client.call_agent_tool(
            manifest.agent_id, _tool.name, params
        )
```

---

## Routing Decision (Jarvis)

1. Classify intent (LLM or rule-based)
2. Query `agent-registry` KV for all registered agents
3. Filter agents whose `intents` include the classified intent
4. Select highest `confidence` match
5. Tiebreak by lowest `queue_depth` (from heartbeat)
6. Dispatch to selected agent

---

## Design Decisions

- DDR-002: Publish full AgentManifest for fleet registration (no separate payload wrapper)
- ADR-004: Dynamic Fleet Registration (CAN Bus Pattern) -- source decision
