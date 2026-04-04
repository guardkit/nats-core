# nats-core System Spec — Addendum: Feature 6 (Fleet Registration)

## Merge Instructions

Add these to `nats-core-system-spec.md`:
1. Add `fleet.py` to package structure under `events/`
2. Add 3 new EventType values to the enum
3. Add Fleet registration schemas to Key Payload Schemas
4. Add Topics.Fleet to the Topic Registry
5. Add Feature 6 section (below) before Non-Functional Requirements
6. Add fleet convenience methods to Feature 4 (NATS Client)

---

## Updates to EventType Enum (Feature 2)

Add to the EventType enum:

```python
    # Fleet registration events (CAN bus pattern — agents self-announce)
    AGENT_REGISTER = "agent_register"
    AGENT_DEREGISTER = "agent_deregister"
    AGENT_HEARTBEAT = "agent_heartbeat"
```

---

## New Schemas (Feature 2 — Key Payload Schemas)

Add after DispatchPayload:

```python
# Fleet registration (CAN bus pattern — agents self-announce capabilities)
class IntentCapability(BaseModel):
    """A single intent this agent can handle, with confidence scoring."""
    pattern: str              # e.g., "product.document", "ideate", "software.build"
    signals: list[str]        # Signal words/phrases that indicate this intent
    confidence: float         # 0.0-1.0 — how well this agent handles this intent
    description: str          # Human-readable description of this capability

class AgentRegistrationPayload(BaseModel):
    """Published by agents on startup to fleet.register.

    Jarvis builds its routing table from these registrations.
    Analogous to a CAN bus device announcing its capabilities on the bus.
    """
    agent_id: str                       # e.g., "product-owner-agent"
    name: str                           # Human-readable: "Product Owner Agent"
    template: str                       # e.g., "langchain-deepagents-weighted-evaluation"
    intents: list[IntentCapability]     # What this agent can handle
    max_concurrent: int = 1             # How many tasks can run in parallel
    status: Literal["ready", "starting", "degraded"] = "ready"
    version: str = "0.1.0"             # Agent software version
    container_id: str | None = None     # Docker container ID if containerised
    metadata: dict[str, str] | None = None  # Extensible agent-specific metadata

class AgentHeartbeatPayload(BaseModel):
    """Published periodically by agents to fleet.heartbeat.{agent_id}.

    Jarvis watches for heartbeat timeouts to detect agents that have gone down.
    """
    agent_id: str
    status: Literal["ready", "busy", "degraded", "draining"]
    queue_depth: int = 0                # Pending tasks in this agent's queue
    active_tasks: int = 0               # Currently executing tasks
    uptime_seconds: int
    last_task_completed_at: datetime | None = None

class AgentDeregistrationPayload(BaseModel):
    """Published by agents on graceful shutdown to fleet.deregister."""
    agent_id: str
    reason: str = "shutdown"            # "shutdown", "maintenance", "error"
```

---

## New Topics (Feature 3 — Topic Registry)

Add after Topics.Jarvis:

```python
    class Fleet:
        """Agent fleet registration and discovery (CAN bus pattern)."""
        REGISTER = "fleet.register"
        DEREGISTER = "fleet.deregister"
        HEARTBEAT = "fleet.heartbeat.{agent_id}"
        HEARTBEAT_ALL = "fleet.heartbeat.>"
        ALL = "fleet.>"
```

---

## Feature 6: Fleet Registration (CAN Bus Pattern)

Dynamic agent discovery — agents self-announce capabilities on startup, and Jarvis
builds its routing table automatically. No router code changes when adding new agents.

### Design Principles

- **CAN bus analogy** — Like devices on a vehicle CAN bus, agents announce what they
  can do when they come online. The router (Jarvis) listens and builds a capability map.
- **MCP-like capability advertising** — Each agent declares its intents, confidence
  scores, and concurrency limits. Jarvis picks the best agent for each request.
- **Heartbeat-based liveness** — Agents that stop heartbeating are marked unavailable.
- **KV-backed routing table** — The agent registry lives in NATS KV (`agent-registry`
  bucket) so it survives Jarvis restarts without requiring all agents to re-register.

### Lifecycle

```
Agent starts  → publishes AgentRegistration to fleet.register
              → Jarvis updates routing table in agent-registry KV
              → Agent begins heartbeating to fleet.heartbeat.{agent_id}

Agent running → periodic heartbeat every 30s
              → Jarvis watches fleet.heartbeat.> for timeout detection
              → If no heartbeat for 90s, Jarvis marks agent as unavailable

Agent stops   → publishes AgentDeregistration to fleet.deregister
              → Jarvis removes from routing table
```

### Routing Decision

When Jarvis receives a request, it:
1. Classifies the intent (lightweight LLM call or rule-based)
2. Queries the agent-registry KV for all registered agents
3. Filters to agents whose `intents` include the classified intent
4. Selects the agent with highest `confidence` for that intent
5. If multiple agents tie, picks the one with lowest `queue_depth`
6. Dispatches to the selected agent

### Acceptance Criteria (BDD)

```gherkin
Feature: Fleet Registration

  Scenario: Agent registers on startup
    Given the Product Owner Agent starts
    When it publishes an AgentRegistrationPayload to fleet.register
    Then the payload should include agent_id "product-owner-agent"
    And it should declare at least one intent capability
    And each intent should have a confidence score between 0.0 and 1.0

  Scenario: Registration includes signal words for intent matching
    Given an AgentRegistrationPayload for the Ideation Agent
    Then it should declare intent "ideate" with signals including "explore", "brainstorm"
    And it should declare intent "ideate" with confidence >= 0.8

  Scenario: Heartbeat tracks agent health
    Given a registered agent "ideation-agent"
    When it publishes an AgentHeartbeatPayload
    Then the payload should include current queue_depth and active_tasks
    And status should be one of "ready", "busy", "degraded", "draining"

  Scenario: Heartbeat timeout marks agent unavailable
    Given a registered agent "architect-agent" with heartbeat interval 30s
    When no heartbeat is received for 90 seconds
    Then Jarvis should mark the agent as unavailable in the routing table

  Scenario: Graceful deregistration removes from routing table
    Given a registered agent "youtube-planner"
    When it publishes an AgentDeregistrationPayload with reason "shutdown"
    Then Jarvis should remove it from the routing table

  Scenario: New agent auto-discovered without router changes
    Given Jarvis is running with 3 registered agents
    When a new agent "product-owner-agent" publishes a registration
    Then Jarvis should add it to the routing table
    And no code changes to Jarvis were required

  Scenario: Confidence-based routing selects best agent
    Given ideation-agent declares "ideate" with confidence 0.9
    And general-purpose-agent declares "ideate" with confidence 0.3
    When a request with intent "ideate" arrives
    Then Jarvis should dispatch to ideation-agent

  Scenario: Queue-aware routing for tied confidence
    Given two guardkitfactory instances both with confidence 1.0
    And instance-1 has queue_depth 3 and instance-2 has queue_depth 0
    When a new "software.build" request arrives
    Then Jarvis should dispatch to instance-2

  Scenario: Registration survives Jarvis restart
    Given 5 agents are registered in the agent-registry KV bucket
    When Jarvis restarts
    Then all 5 agents should be in the routing table from KV

  Scenario: Concurrent task limit via max_concurrent
    Given guardkitfactory registers with max_concurrent=2 and active_tasks=2
    When a new "software.build" request arrives
    Then Jarvis should queue or route to another capable agent
```

### NATSClient Convenience Methods (add to Feature 4)

```python
async def register_agent(self, registration: AgentRegistrationPayload) -> None:
    """Publish agent registration and store in KV."""

async def deregister_agent(self, agent_id: str, reason: str = "shutdown") -> None:
    """Publish deregistration and remove from KV."""

async def heartbeat(self, heartbeat: AgentHeartbeatPayload) -> None:
    """Publish agent heartbeat."""

async def get_fleet_registry(self) -> dict[str, AgentRegistrationPayload]:
    """Read all registered agents from KV bucket."""

async def watch_fleet(self, callback) -> None:
    """Watch for fleet registration/deregistration/heartbeat events."""
```

---

## Updated Package Structure

```
nats-core/
├── src/
│   └── nats_core/
│       ├── events/
│       │   ├── pipeline.py
│       │   ├── agent.py
│       │   ├── jarvis.py
│       │   └── fleet.py         ← NEW: AgentRegistration, Heartbeat, Deregistration
│       ├── topics.py            ← UPDATED: add Topics.Fleet
│       └── ...
```
