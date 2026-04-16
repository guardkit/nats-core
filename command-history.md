/task-create please create a task: Task: Merge fleet registration addendum into parent spec
Read both files:

docs/design/specs/nats-core-system-spec.md (parent)
docs/design/specs/nats-core-spec-addendum-fleet-registration.md (addendum)

The addendum has explicit merge instructions at the top. Follow them precisely:

Add fleet.py to the package structure under events/ in the repo structure section
Add 3 new EventType values (AGENT_REGISTER, AGENT_DEREGISTER, AGENT_HEARTBEAT) to the EventType enum in Feature 2
Add the Fleet registration schemas (IntentCapability, AgentRegistrationPayload, AgentHeartbeatPayload, AgentDeregistrationPayload) to the Key Payload Schemas section in Feature 2
Add Topics.Fleet (REGISTER, DEREGISTER, HEARTBEAT, HEARTBEAT_ALL, ALL) to the Topic Registry in Feature 3
Add the entire Feature 6 section (Fleet Registration with design principles, lifecycle, routing decision, BDD acceptance criteria) as a new feature section before Non-Functional Requirements
Add fleet convenience methods (register_agent, deregister_agent, heartbeat, get_fleet_registry, watch_fleet) to the NATSClient in Feature 4

Important: Also add these elements that were designed after the addendum was written:

Add agents.{agent_id}.tools.{tool_name} and agents.{agent_id}.tools.> to Topics under a new Topics.Agents class, alongside the existing Topics.Fleet — this is for direct agent-to-agent tool invocation
Add a call_agent_tool(agent_id, tool_name, params) convenience method to the NATSClient in Feature 4
In the package structure, add manifest.py to the top level of nats_core/ — this will hold AgentManifest, ToolCapability, IntentCapability (see docs/design/contracts/agent-manifest-contract.md for the schema)

After merging, verify the document reads as one coherent spec with no duplicate sections. Then delete the addendum file nats-core-spec-addendum-fleet-registration.md.
Commit with message: "Merge fleet registration addendum into system spec, add agent tool topics and manifest"


Task TASK-B527 Complete — IN_REVIEW

All merge operations applied to nats-core-system-spec.md:

Acceptance Criteria	Status
fleet.py added to package structure under events/	Done
manifest.py added to top level of nats_core/	Done
3 new EventType values (AGENT_REGISTER/DEREGISTER/HEARTBEAT)	Done
Fleet registration schemas (IntentCapability, AgentRegistration/Heartbeat/Deregistration)	Done
Topics.Fleet (REGISTER, DEREGISTER, HEARTBEAT, HEARTBEAT_ALL, ALL)	Done
Topics.Agents tool topics (TOOLS, TOOLS_ALL)	Done
Feature 6 section (Fleet Registration) before Non-Functional Requirements	Done
Fleet convenience methods + call_agent_tool on NATSClient	Done
Addendum file deleted	Done
Committed with requested message	Done





/system-arch \
  --from docs/design/specs/nats-core-system-spec.md \
  --context docs/design/decisions/ADR-001-nats-as-event-bus.md \
  --context docs/design/decisions/ADR-004-dynamic-fleet-registration.md


All seeding complete.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GRAPHITI SEEDING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Artefact	Nodes	Edges
domain-model.md	26	31
ARCHITECTURE.md	26	43
ADR-ARCH-001 (modular monolith)	7	6
ADR-ARCH-002 (Python 3.12+)	2	1
ADR-ARCH-003 (minimal deps)	7	6
Total	68	87
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE DOCUMENTATION COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


docs/architecture/
  ├── ARCHITECTURE.md          (index + summary)
  ├── domain-model.md          (entities, relationships, topic structure)
  ├── system-context.md        (C4 Level 1)
  ├── container.md             (C4 Level 2)
  ├── assumptions.yaml         (10 assumptions)
  └── decisions/
      ├── ADR-ARCH-001-modular-monolith-pattern.md
      ├── ADR-ARCH-002-python-312-minimum.md
      └── ADR-ARCH-003-minimal-runtime-dependencies.md
All artefacts seeded to Graphiti (68 nodes, 87 edges) and queryable by downstream commands.

Next steps:

Review: ARCHITECTURE.md
Design APIs: /system-design with the system spec
Plan features: /system-plan for implementation planning



/system-design \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/design/specs/nats-core-system-spec.md \
  --context docs/design/decisions/ADR-002-schema-versioning.md \
  --context docs/design/decisions/ADR-003-nats-py-vs-faststream.md

🏗️ Architecture loaded: 6 modules (Envelope, Events, Manifest, Topics, Client, Config)
🔄 Existing design context found — 4 ADRs, 1 system spec, 1 manifest contract
⚠️ Graphiti enabled in config — connectivity will be checked at seeding phase.

Since nats-core is a shared library (not a microservices system), the "bounded contexts" map to logical domains within the library. I've identified 4 design units based on the architecture:

#	Design Unit	Modules	Responsibility
1	Message Contracts	envelope.py, events/	Wire format + typed payload schemas
2	Fleet Registration	manifest.py, fleet events	Agent capability declaration + discovery
3	Topic Registry	topics.py	Subject naming, resolution, project scoping
4	NATS Client & Config	client.py, config.py	Connection, typed pub/sub, runtime config
Before we begin the per-unit interactive design, a few scoping questions:

AskUserQuestion
OUT
User has answered your questions: "Which protocol surfaces should nats-core define contracts for?"="NATS Events (Recommended), MCP Tool Definitions, Python Public API", "Should we design all 4 units or focus on a specific one first?"="All 4 design units", "The existing system spec and manifest contract are detailed. Should we build on them or start fresh?"="Build on existing (Recommended)". You can now continue with the user's answers in mind.
Excellent. Full design pass across all 4 units, building on existing specs, with NATS Events, MCP Tool Definitions, and Python Public API surfaces.

Let's begin.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 DESIGNING: Unit 1 — Message Contracts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Modules: envelope.py, events/ (pipeline, agent, jarvis, fleet)
Responsibility: Wire format for all NATS messages + typed payload schemas per domain

📡 API CONTRACT: Message Contracts
From the system spec, the primary operations are:

Operation	Description
Create envelope	Construct MessageEnvelope with auto-generated ID/timestamp
Serialise/deserialise	model_dump_json() / model_validate_json() round-trip
Forward compatibility	Unknown fields silently ignored (extra="ignore")
Payload dispatch	event_type discriminator selects the correct payload model
Correlation	correlation_id links related messages across the fleet
Proposed Python Public API for this unit:


# From nats_core — public re-exports
from nats_core.envelope import MessageEnvelope
from nats_core.envelope import EventType

# Event payloads — pipeline domain
from nats_core.events.pipeline import (
    FeaturePlannedPayload, BuildProgressPayload,
    BuildCompletePayload, BuildFailedPayload,
)

# Event payloads — agent domain
from nats_core.events.agent import (
    AgentStatusPayload, ApprovalRequestPayload, ApprovalResponsePayload,
)

# Event payloads — jarvis domain
from nats_core.events.jarvis import (
    IntentClassifiedPayload, DispatchPayload,
)

# Event payloads — fleet domain
from nats_core.events.fleet import (
    AgentRegistrationPayload, AgentHeartbeatPayload, AgentDeregistrationPayload,
)

# Helper: resolve payload class from EventType
from nats_core.envelope import payload_class_for_event_type
NATS Event contracts (wire format):

Event Type	Topic Pattern	Payload Model	Direction
feature_planned	pipeline.feature-planned.{feature_id}	FeaturePlannedPayload	Published
build_started	pipeline.build-started.{feature_id}	BuildStartedPayload	Published
build_progress	pipeline.build-progress.{feature_id}	BuildProgressPayload	Published
build_complete	pipeline.build-complete.{feature_id}	BuildCompletePayload	Published
build_failed	pipeline.build-failed.{feature_id}	BuildFailedPayload	Published
status	agents.status.{agent_id}	AgentStatusPayload	Published
approval_request	agents.approval.{agent_id}.{task_id}	ApprovalRequestPayload	Published
approval_response	agents.approval.{agent_id}.{task_id}.response	ApprovalResponsePayload	Published
intent_classified	jarvis.intent.classified	IntentClassifiedPayload	Published
dispatch	jarvis.dispatch.{agent}	DispatchPayload	Published
agent_register	fleet.register	AgentRegistrationPayload	Published
agent_heartbeat	fleet.heartbeat.{agent_id}	AgentHeartbeatPayload	Published
agent_deregister	fleet.deregister	AgentDeregistrationPayload	Published
📊 DATA MODEL: Message Contracts
Core entities (from system spec + domain model):


MessageEnvelope (root)
  ├── message_id: UUID v4 (auto-generated)
  ├── timestamp: datetime UTC (auto-generated)
  ├── version: str = "1.0"
  ├── source_id: str (originating service)
  ├── event_type: EventType (discriminator)
  ├── project: str | None (multi-tenancy scope)
  ├── correlation_id: str | None (links related messages)
  └── payload: dict[str, Any] (event-specific data)

EventType (str, Enum)
  ├── Pipeline: 7 values
  ├── Agent: 6 values
  ├── Jarvis: 4 values
  └── Fleet: 3 values
Invariants:

Every EventType value MUST have a corresponding Pydantic payload class
MessageEnvelope.extra = "ignore" — always tolerate unknown fields
New payload fields MUST be optional with defaults (ADR-002)
build_id format: build-{feature_id}-{YYYYMMDDHHMMSS}
overall_progress_pct constrained to 0.0–100.0
confidence fields constrained to 0.0–1.0
AskUserQuestion
OUT
User has answered your questions: "Does the Message Contracts design look correct? Should I add a payload_class_for_event_type() helper to the public API, or keep it simple with direct imports only?"="Add helper (Recommended)", "Should we add a ready_for_dev and ticket_updated event (from the EventType enum) to the pipeline payload schemas? The system spec lists them in EventType but doesn't define payload classes."="In the revised model:

ticket_updated should be dropped entirely — there are no tickets. It has no role in a context-first pipeline.
ready_for_dev needs to be redesigned, not just added. The trigger is no longer "a human moved a Kanban card." It's the Pipeline Orchestrator Agent completing the appropriate GuardKit command sequence (/system-arch → /system-design → /system-plan for greenfield, or /feature-spec → /feature-plan for existing) and signalling that the feature spec is ready to hand off to AutoBuild.

So the event that replaces ready_for_dev is something like pipeline_stage_complete or feature_ready_for_build — emitted by the Pipeline Orchestrator, not by a webhook from a PM tool. The payload shape is also different: it carries the output artefact paths from the GuardKit commands (the feature spec YAML, the plan), not a ticket ID.
The practical instruction to give the tool: "Drop ticket_updated. Redesign ready_for_dev as an orchestrator-emitted event — feature_ready_for_build — published by the Pipeline Orchestrator Agent after completing the relevant GuardKit command sequence. Payload should include feature_id, spec_path, plan_path, and pipeline_type (greenfield | existing)."". You can now continue with the user's answers in mind.
Excellent feedback. Updating the design:

Changes captured:

TICKET_UPDATED dropped from EventType — no tickets in context-first pipeline
READY_FOR_DEV → FEATURE_READY_FOR_BUILD — emitted by Pipeline Orchestrator Agent after completing GuardKit command sequence
payload_class_for_event_type() helper added to public API
New event:


class FeatureReadyForBuildPayload(BaseModel):
    """Emitted by Pipeline Orchestrator Agent when GuardKit command sequence
    completes and the feature is ready for AutoBuild handoff."""
    feature_id: str
    spec_path: str          # Path to feature spec YAML
    plan_path: str          # Path to feature plan
    pipeline_type: Literal["greenfield", "existing"]
    source_commands: list[str] = []  # e.g. ["/system-arch", "/system-design", "/system-plan"]
Updated EventType enum (pipeline domain):


# Pipeline events — REVISED
FEATURE_PLANNED = "feature_planned"
FEATURE_READY_FOR_BUILD = "feature_ready_for_build"   # was READY_FOR_DEV
BUILD_STARTED = "build_started"
BUILD_PROGRESS = "build_progress"
BUILD_COMPLETE = "build_complete"
BUILD_FAILED = "build_failed"
# TICKET_UPDATED — REMOVED (no tickets in context-first pipeline)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ DESIGN CHECKPOINT: Message Contracts
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

API Contracts:

Python Public API: 15+ model re-exports + payload_class_for_event_type() helper
NATS Events: 12 event types with topic mappings (was 13, dropped ticket_updated)
Data Model:

2 core entities (MessageEnvelope, EventType)
12 payload models across 4 domains
6 invariants
Key design change: READY_FOR_DEV → FEATURE_READY_FOR_BUILD (orchestrator-emitted, carries artefact paths not ticket IDs)

This is a DDR-worthy decision. I'll capture it now.

📝 DDR-001: Replace READY_FOR_DEV with FEATURE_READY_FOR_BUILD

Field	Value
Context	The original READY_FOR_DEV event was modelled after Kanban card movement by a PM tool webhook. In the context-first pipeline, features are ready for build when the Pipeline Orchestrator Agent completes a GuardKit command sequence, not when a human moves a card.
Decision	Replace READY_FOR_DEV with FEATURE_READY_FOR_BUILD. Drop TICKET_UPDATED entirely.
Rationale	No ticket system exists in the pipeline. The trigger is the Pipeline Orchestrator completing /feature-spec → /feature-plan (existing) or /system-arch → /system-design → /system-plan (greenfield). Payload carries artefact paths (spec_path, plan_path, pipeline_type) instead of ticket IDs.
Alternatives	Keep READY_FOR_DEV with different payload (confusing name), Add webhook integration later (YAGNI)
Status	Accepted
Now moving to Design Unit 2.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 DESIGNING: Unit 2 — Fleet Registration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Modules: manifest.py, fleet events in events/fleet.py
Responsibility: Agent capability declaration, discovery, and routing table

The existing agent-manifest-contract.md is detailed. Building on it.

📡 API CONTRACT: Fleet Registration
Python Public API:


# Manifest models
from nats_core.manifest import AgentManifest, IntentCapability, ToolCapability

# Fleet event payloads (already in Unit 1)
from nats_core.events.fleet import (
    AgentRegistrationPayload, AgentHeartbeatPayload, AgentDeregistrationPayload,
)

# Registry interface
from nats_core.manifest import ManifestRegistry
NATS Event contracts:

Operation	Topic	Payload	Direction
Agent registers	fleet.register	AgentRegistrationPayload (wraps AgentManifest)	Pub
Agent heartbeat	fleet.heartbeat.{agent_id}	AgentHeartbeatPayload	Pub (periodic 30s)
Agent deregisters	fleet.deregister	AgentDeregistrationPayload	Pub
Tool invocation	agents.{agent_id}.tools.{tool_name}	Request/reply JSON	Req/Rep
MCP Tool Definitions (derived from AgentManifest.tools):

Each ToolCapability in a manifest maps 1:1 to an MCP tool:


{
  "name": "architect:run_architecture_session",
  "description": "Run a full architecture design session",
  "inputSchema": { /* from ToolCapability.parameters */ },
  "annotations": {
    "risk_level": "mutating",
    "requires_approval": false,
    "async_mode": true
  }
}
📊 DATA MODEL: Fleet Registration
Entities (from manifest contract):


AgentManifest (root)
  ├── agent_id: str (PK)
  ├── name: str
  ├── version: str (semver)
  ├── intents: list[IntentCapability]
  ├── tools: list[ToolCapability]
  ├── template: str
  ├── max_concurrent: int = 1
  ├── status: "ready" | "starting" | "degraded"
  ├── trust_tier: "core" | "specialist" | "extension"
  ├── required_permissions: list[str]
  └── metadata: dict[str, str]

IntentCapability
  ├── pattern: str (e.g., "software.build")
  ├── signals: list[str]
  ├── confidence: float (0.0-1.0)
  └── description: str

ToolCapability
  ├── name: str
  ├── description: str
  ├── parameters: dict[str, Any] (JSON Schema)
  ├── returns: str
  ├── risk_level: "read_only" | "mutating" | "destructive"
  ├── async_mode: bool
  └── requires_approval: bool

ManifestRegistry (abstract interface)
  ├── register(manifest) -> None
  ├── deregister(agent_id) -> None
  ├── get(agent_id) -> AgentManifest | None
  ├── list_all() -> list[AgentManifest]
  ├── find_by_intent(intent) -> list[AgentManifest]
  └── find_by_tool(tool_name) -> list[AgentManifest]
Invariants:

agent_id must be unique in the registry
confidence constrained to 0.0–1.0
ToolCapability.parameters must be valid JSON Schema
ManifestRegistry backed by NATS KV (agent-registry bucket)
Heartbeat timeout: 90s without heartbeat → agent marked unavailable
Relationships:

AgentManifest 1→N IntentCapability (routing)
AgentManifest 1→N ToolCapability (direct invocation)
AgentRegistrationPayload wraps/derives from AgentManifest
ManifestRegistry stores AgentManifest instances
AskUserQuestion
OUT
User has answered your questions: "The manifest contract defines AgentRegistrationPayload separately from AgentManifest. Should registration just publish the full AgentManifest directly, or keep a separate lighter payload?"="Publish full manifest", "Should ManifestRegistry be an abstract base class in nats-core, or just the NATS KV implementation?"="ABC + NATS KV impl". You can now continue with the user's answers in mind.
Decisions captured:

fleet.register publishes the full AgentManifest directly — no separate AgentRegistrationPayload wrapper. Simpler, one model. The AgentManifest goes into MessageEnvelope.payload.
ManifestRegistry ABC + NATSKVManifestRegistry — ABC in manifest.py, NATS KV implementation in client.py. Enables InMemoryManifestRegistry for testing.
This simplifies the fleet event model:

AgentRegistrationPayload → removed, use AgentManifest directly as payload
AgentHeartbeatPayload → kept (different shape, lightweight periodic data)
AgentDeregistrationPayload → kept (minimal: agent_id + reason)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ DESIGN CHECKPOINT: Fleet Registration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

API Contracts:

Python API: AgentManifest, IntentCapability, ToolCapability, ManifestRegistry ABC
NATS Events: 3 fleet events (register publishes full manifest)
MCP: 1:1 mapping from ToolCapability → MCP tool definition
Data Model:

4 entities (AgentManifest, IntentCapability, ToolCapability, ManifestRegistry)
5 invariants
DDR-002: Publish full AgentManifest for fleet registration

Field	Value
Context	Original design had separate AgentRegistrationPayload wrapping AgentManifest with extra fields. Two models for one concept.
Decision	Drop AgentRegistrationPayload. Publish AgentManifest directly as the MessageEnvelope.payload on fleet.register.
Rationale	Single model, no duplication. container_id and metadata are already on AgentManifest. KV stores the same object that was published.
Alternatives	Keep separate payload (independent evolution), Embed manifest in payload dict (hybrid)
Status	Accepted
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 DESIGNING: Unit 3 — Topic Registry
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Module: topics.py
Responsibility: Typed constants for all NATS subjects — no magic strings anywhere

📡 API CONTRACT: Topic Registry
Python Public API:


from nats_core.topics import Topics

# Nested classes for namespacing
Topics.Pipeline.BUILD_STARTED        # "pipeline.build-started.{feature_id}"
Topics.Pipeline.ALL                  # "pipeline.>"
Topics.Agents.STATUS                 # "agents.status.{agent_id}"
Topics.Agents.TOOLS                  # "agents.{agent_id}.tools.{tool_name}"
Topics.Fleet.REGISTER                # "fleet.register"
Topics.Fleet.HEARTBEAT               # "fleet.heartbeat.{agent_id}"
Topics.Jarvis.DISPATCH               # "jarvis.dispatch.{agent}"
Topics.System.HEALTH                 # "system.health.{component}"

# Resolution helpers
Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="FEAT-001")
# → "pipeline.build-started.FEAT-001"

Topics.for_project("finproxy", "pipeline.build-started.FEAT-001")
# → "finproxy.pipeline.build-started.FEAT-001"
Topic hierarchy (all domains):


pipeline.
  ├── feature-planned.{feature_id}
  ├── feature-ready-for-build.{feature_id}    # NEW (was ready-for-dev)
  ├── build-started.{feature_id}
  ├── build-progress.{feature_id}
  ├── build-complete.{feature_id}
  ├── build-failed.{feature_id}
  └── >                                        # wildcard: all pipeline

agents.
  ├── status.{agent_id}
  ├── status.>                                 # wildcard: all status
  ├── approval.{agent_id}.{task_id}
  ├── approval.{agent_id}.{task_id}.response
  ├── command.{agent_id}
  ├── result.{agent_id}
  ├── {agent_id}.tools.{tool_name}
  └── {agent_id}.tools.>                       # wildcard: all tools for agent

fleet.
  ├── register
  ├── deregister
  ├── heartbeat.{agent_id}
  ├── heartbeat.>                              # wildcard: all heartbeats
  └── >                                        # wildcard: all fleet

jarvis.
  ├── command.{adapter}
  ├── intent.classified
  ├── dispatch.{agent}
  └── notification.{adapter}                   # was notifications.{adapter}

system.
  └── health.{component}
📊 DATA MODEL: Topic Registry
Invariants:

All topic templates are str constants — no runtime computation
Topics.resolve() raises KeyError if a required placeholder is missing
Topics.for_project() prepends project scope — always {project}.{topic}
Wildcard subjects use NATS > (multi-level) only, never * (single-level) for "all" patterns
Topic names use kebab-case for event segments (build-started, not build_started)
AskUserQuestion
OUT
User has answered your questions: "The system spec has notifications.{adapter} but Jarvis domain uses jarvis.* prefix. Should notification topics be jarvis.notification.{adapter} or stay at the top level?"="jarvis.notification.{adapter}", "Should Topics expose an ALL_TOPICS list for tooling (e.g., NATS stream setup, monitoring dashboards)?"="Yes, add ALL_TOPICS". You can now continue with the user's answers in mind.
Decisions captured:

notifications.{adapter} → jarvis.notification.{adapter} — consistent namespace, easier account isolation
Topics.ALL_TOPICS: list[str] added — enumerates all template strings for stream setup and monitoring
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ DESIGN CHECKPOINT: Topic Registry
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

API Contracts:

Python API: Topics class with nested namespaces, resolve(), for_project(), ALL_TOPICS
NATS Events: 20 topic templates across 5 domains
Data Model:

1 entity (Topics — static registry)
5 invariants
Straightforward unit — no DDR needed. Moving on.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 DESIGNING: Unit 4 — NATS Client & Config
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Modules: client.py, config.py
Responsibility: Typed pub/sub wrapper, fleet convenience methods, runtime config

📡 API CONTRACT: NATS Client & Config
Python Public API:


from nats_core.client import NATSClient
from nats_core.config import NATSConfig, AgentConfig, ModelConfig, GraphitiConfig

# Core client lifecycle
client = NATSClient(config=NATSConfig())
await client.connect()
await client.disconnect()

# Typed publish (wraps in MessageEnvelope automatically)
await client.publish(
    topic=Topics.Pipeline.BUILD_COMPLETE,
    payload=BuildCompletePayload(...),
    event_type=EventType.BUILD_COMPLETE,
    source_id="guardkit-factory",
    project="finproxy",               # optional scoping
    correlation_id="session-abc-123",  # optional correlation
)

# Typed subscribe (unwraps MessageEnvelope, delivers typed callback)
await client.subscribe(
    topic=Topics.Pipeline.BUILD_COMPLETE,
    callback=handle_build_complete,    # async def handler(envelope: MessageEnvelope)
)

# Fleet convenience methods
await client.register_agent(manifest: AgentManifest)
await client.deregister_agent(agent_id: str, reason: str = "shutdown")
await client.heartbeat(heartbeat: AgentHeartbeatPayload)
await client.get_fleet_registry() -> dict[str, AgentManifest]
await client.watch_fleet(callback)

# Agent-to-agent tool invocation (request/reply)
result = await client.call_agent_tool(
    agent_id="architect-agent",
    tool_name="run_architecture_session",
    params={"docs_path": "...", "scope": "..."},
    timeout=30.0,
)

# ManifestRegistry implementations
from nats_core.client import NATSKVManifestRegistry
from nats_core.manifest import InMemoryManifestRegistry  # for testing
Config hierarchy:


NATSConfig (pydantic-settings, env_prefix="NATS_")
  ├── url: str = "nats://localhost:4222"
  ├── connect_timeout: float = 5.0
  ├── reconnect_time_wait: float = 2.0
  ├── max_reconnect_attempts: int = 60
  ├── name: str = "nats-core-client"
  ├── user: str | None
  ├── password: str | None
  └── creds_file: str | None

AgentConfig (pydantic-settings, env_prefix="AGENT_", env_nested_delimiter="__")
  ├── models: ModelConfig
  │     ├── reasoning_model: str
  │     ├── reasoning_endpoint: str = ""
  │     ├── implementation_model: str | None
  │     ├── implementation_endpoint: str | None
  │     ├── embedding_model: str | None
  │     └── embedding_endpoint: str | None
  ├── graphiti: GraphitiConfig | None
  │     ├── endpoint: str = "bolt://localhost:7687"
  │     └── default_group_ids: list[str]
  ├── nats: NATSConfig
  ├── langsmith_project: str | None
  ├── langsmith_api_key: str | None
  ├── heartbeat_interval_seconds: int = 30
  ├── heartbeat_timeout_seconds: int = 90
  ├── max_task_timeout_seconds: int = 600
  └── {provider}_api_key: str | None  (gemini, anthropic, openai)
📊 DATA MODEL: NATS Client & Config
Invariants:

NATSClient wraps nats-py only — no FastStream dependency (ADR-003)
All publish operations auto-wrap in MessageEnvelope
connect() retries with exponential backoff on transient failures
disconnect() drains all subscriptions before closing
call_agent_tool() uses NATS request/reply pattern with configurable timeout
NATSConfig loads from environment variables (NATS_URL, NATS_CREDS_FILE, etc.)
AgentConfig never appears in AgentManifest — private local config only
AskUserQuestion
OUT
User has answered your questions: "Should NATSClient.publish() accept EventType + payload separately (explicit dispatch), or infer event_type from the payload class (convention-based)?"="Explicit (Recommended)", "Should AgentConfig be in config.py alongside NATSConfig, or in a separate agent_config.py module?"="Separate modules". You can now continue with the user's answers in mind.
Decisions captured:

Explicit event_type on publish() — no inference, clear at call site
Separate modules — config.py for NATSConfig, agent_config.py for AgentConfig/ModelConfig/GraphitiConfig
Updated package structure:


src/nats_core/
  ├── config.py          # NATSConfig (nats-core connection)
  ├── agent_config.py    # AgentConfig, ModelConfig, GraphitiConfig (fleet-wide)
  └── ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ DESIGN CHECKPOINT: NATS Client & Config
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

API Contracts:

Python API: NATSClient (typed pub/sub, fleet methods, tool calls), NATSConfig, AgentConfig
NATS Events: Envelope auto-wrapping on publish, unwrapping on subscribe
MCP: call_agent_tool() enables NATS-backed agent tool invocation
Data Model:

5 entities (NATSClient, NATSConfig, AgentConfig, ModelConfig, GraphitiConfig)
7 invariants
All 4 design units complete. Moving to contradiction detection.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ CONTRADICTION DETECTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Checking proposed contracts against existing ADRs (ADR-001 through ADR-004, ADR-ARCH-001 through ADR-ARCH-003)...

Contract	ADR	Result
NATS Events (all domains)	ADR-001 (NATS as event bus)	✓ Aligned
extra="ignore" on all models	ADR-002 (schema versioning)	✓ Aligned
NATSClient wraps nats-py	ADR-003 (nats-py for core, FastStream for services)	✓ Aligned
fleet.register publishes AgentManifest	ADR-004 (dynamic fleet registration)	✓ Aligned — simplifies by removing AgentRegistrationPayload
FEATURE_READY_FOR_BUILD replacing READY_FOR_DEV	ADR-002 (schema versioning)	⚠️ Minor: this is a breaking event type rename — requires major version bump per ADR-002 rule 6
Note on FEATURE_READY_FOR_BUILD: Since nats-core is not yet published (v0.x), the rename is non-breaking. ADR-002's semver rules apply from v1.0 onwards. No action needed now.

✓ No contradictions detected. All proposed contracts align with existing ADRs.

Now generating output artefacts. I'll create:

API contract files per design unit
Data model files per design unit
MCP tool definition template
DDR-001 and DDR-002
Updated package structure diagram

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 C4 COMPONENT DIAGRAM REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The nats-core library has 7 internal components, exceeding the >3 threshold:


C4Component
    title nats-core Components

    Component(envelope, "envelope.py", "Pydantic", "MessageEnvelope, EventType, dispatch helper")
    Component(events, "events/", "Pydantic", "Pipeline, Agent, Jarvis, Fleet payloads")
    Component(manifest, "manifest.py", "Pydantic", "AgentManifest, capabilities, registry ABC")
    Component(topics, "topics.py", "Python", "Topic constants, resolve(), for_project()")
    Component(client, "client.py", "nats-py", "NATSClient, NATSKVManifestRegistry")
    Component(config, "config.py", "pydantic-settings", "NATSConfig")
    Component(agent_config, "agent_config.py", "pydantic-settings", "AgentConfig, ModelConfig")

    Rel(client, config, "Reads settings")
    Rel(client, topics, "Resolves topics")
    Rel(client, envelope, "Wraps/unwraps")
    Rel(client, manifest, "KV registry impl")
    Rel(events, envelope, "Payloads in envelope")
    Rel(manifest, events, "Fleet event types")
    Rel(agent_config, config, "Nests NATSConfig")
Look for: components with too many dependencies, missing persistence layers, unclear separation.

Key observations:

client.py has 4 internal dependencies (highest fan-in) -- expected, it's the integration point
Clean unidirectional dependency chain: no cycles
agent_config.py separated from config.py per design decision
AskUserQuestion
OUT
User has answered your questions: "Does the C4 L3 component diagram look correct?"="Approve". You can now continue with the user's answers in mind.
✓ C4 L3 diagram approved.

Now checking Graphiti connectivity for seeding.

Graphiti [get_status]
OUT
{"status":"ok","message":"Graphiti MCP server is running and connected to falkordb database"}
✓ Graphiti is running and connected to FalkorDB.

Bash Check if guardkit CLI is available
IN
which guardkit 2>/dev/null || echo "not found"

OUT
/Users/richardwoollcott/.agentecflow/bin/guardkit
Graphiti is connected. Here are the seeding commands for the design artefacts:


# API contracts (4 files)
guardkit graphiti add-context docs/design/contracts/API-message-contracts.md --group project_design
guardkit graphiti add-context docs/design/contracts/API-fleet-registration.md --group project_design
guardkit graphiti add-context docs/design/contracts/API-topic-registry.md --group project_design
guardkit graphiti add-context docs/design/contracts/API-nats-client.md --group project_design

# Data models (3 files)
guardkit graphiti add-context docs/design/models/DM-message-contracts.md --group project_design
guardkit graphiti add-context docs/design/models/DM-fleet-registration.md --group project_design
guardkit graphiti add-context docs/design/models/DM-nats-client.md --group project_design

# Design decisions (2 DDRs)
guardkit graphiti add-context docs/design/decisions/DDR-001-feature-ready-for-build.md --group architecture_decisions
guardkit graphiti add-context docs/design/decisions/DDR-002-publish-full-manifest.md --group architecture_decisions
AskUserQuestion
OUT
User has answered your questions: "Run these 9 Graphiti seeding commands now?"="Yes, seed all". You can now continue with the user's answers in mind.
Running all 9 seeding commands.

Graphiti seeding running in background (3 batches). I'll report results when they complete.

While those run, here's the final summary:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ SYSTEM DESIGN COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Created/updated: docs/design/
  ├── mcp-tools.json                          (MCP tool definition template)
  ├── contracts/
  │   ├── API-message-contracts.md            (envelope + events)
  │   ├── API-fleet-registration.md           (manifest + capabilities)
  │   ├── API-topic-registry.md               (topics + resolution)
  │   ├── API-nats-client.md                  (client + config)
  │   └── agent-manifest-contract.md          (existing — preserved)
  ├── models/
  │   ├── DM-message-contracts.md             (envelope, EventType, payloads)
  │   ├── DM-fleet-registration.md            (manifest, capabilities, registry)
  │   └── DM-nats-client.md                   (client, config, agent_config)
  ├── diagrams/
  │   └── nats-core-components.md             (C4 L3 — 7 components)
  ├── decisions/
  │   ├── ADR-001-nats-as-event-bus.md        (existing)
  │   ├── ADR-002-schema-versioning.md        (existing)
  │   ├── ADR-003-nats-py-vs-faststream.md    (existing)
  │   ├── ADR-004-dynamic-fleet-registration.md (existing)
  │   ├── DDR-001-feature-ready-for-build.md  (NEW)
  │   └── DDR-002-publish-full-manifest.md    (NEW)
  └── specs/
      └── nats-core-system-spec.md            (existing — preserved)
Design artefacts: 4 API contracts, 3 data models, 1 MCP template, 1 C4 L3 diagram, 2 DDRs

Graphiti: Seeding in progress (9 artefacts across 3 batches)

Key design decisions this session:

DDR-001: READY_FOR_DEV → FEATURE_READY_FOR_BUILD (orchestrator-emitted, carries artefact paths); TICKET_UPDATED dropped
DDR-002: Publish full AgentManifest for fleet registration (no separate payload wrapper)
payload_class_for_event_type() helper in public API
notifications.{adapter} → jarvis.notification.{adapter} (consistent namespace)
Topics.ALL_TOPICS list for tooling
Explicit event_type on NATSClient.publish() (no inference)
agent_config.py separate from config.py
ManifestRegistry ABC + NATSKVManifestRegistry + InMemoryManifestRegistry
Next steps:

Review: docs/design/contracts/ and docs/design/models/
Plan features: /feature-plan "message envelope"
Generate specs: /feature-spec "message envelope" --from docs/design/
Refine design: /design-refine


✓ DDRs seeded successfully — DDR-001 (3 nodes, 1 edge) and DDR-002 (5 nodes, 3 edges). Minor warning about missing "Status" section header (the status is in the metadata line — cosmetic only).

Waiting on the contracts and models batches to complete.

Read bzvyvpeiw.output
✓ Data models seeded successfully:

DM-nats-client: 8 nodes, 10 edges
DM-message-contracts: 28 nodes, 55 edges (richest — all payload schemas)
DM-fleet-registration: 8 nodes, 12 edges
Still waiting on the API contracts batch.

Read bulj4d62y.output
All Graphiti seeding complete. Here's the final tally:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ GRAPHITI SEEDING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Artefact	Nodes	Edges
API-fleet-registration	17	15
API-message-contracts	9	14
API-nats-client	12	9
API-topic-registry	29	86
DM-message-contracts	28	55
DM-fleet-registration	8	12
DM-nats-client	8	10
DDR-001	3	1
DDR-002	5	3
Total	119 nodes	205 edges
All 9 artefacts seeded into the knowledge graph. Design context is now queryable by /feature-spec and /feature-plan.





/feature-spec "Message Envelope: base MessageEnvelope schema with versioning and correlation" \
  --context docs/design/specs/nats-core-system-spec.md


Context loaded: stack=python (from CLAUDE.md), 0 models found (src/ not yet created),
0 existing .feature files, 1 ADR (XC-schema-versioning), 1 API contract (API-message-contracts.md)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: Message Envelope
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Feature: Message Envelope
  As a fleet service developer
  I want a base message envelope with versioning and correlation
  So that all NATS messages have a consistent, evolvable wire format

  Background:
    Given the MessageEnvelope schema is available
━━ GROUP A: Key Examples (5 scenarios) ━━


  # Why: Core construction path — envelope populates defaults for optional fields
  @key-example @smoke
  Scenario: Creating an envelope with defaults
    Given no explicit message_id or timestamp
    When I create a MessageEnvelope with source_id "test-agent" and event_type STATUS
    Then message_id should be a valid UUID v4
    And timestamp should be within 1 second of now in UTC
    And version should be "1.0"

  # Why: Wire format must be valid JSON with ISO 8601 timestamps for interop
  @key-example @smoke
  Scenario: Serialising an envelope to JSON
    Given a MessageEnvelope with known field values
    When I serialise it to JSON
    Then the output should be valid JSON
    And timestamp should be in ISO 8601 format
    And all fields should be present in the output

  # Why: Consumers must be able to reconstruct an envelope from the wire format
  @key-example @smoke
  Scenario: Deserialising an envelope from valid JSON
    Given a valid JSON string representing a MessageEnvelope
    When I parse it as a MessageEnvelope
    Then all fields should match the original values
    And message_id should be preserved exactly
    And timestamp should be preserved exactly

  # Why: Correlation ID is the mechanism for linking request-response chains
  @key-example
  Scenario: Correlation ID links related messages
    Given an envelope with correlation_id "session-abc-123"
    When I create a response envelope with the same correlation_id
    Then both envelopes should share the same correlation_id
    And they should have different message_ids
    And they should have different timestamps

  # Why: Project-scoped envelopes support multi-tenancy
  @key-example
  Scenario: Creating an envelope with a project scope
    When I create a MessageEnvelope with project "finproxy" and source_id "guardkit-factory"
    Then the project field should be "finproxy"
    And all other default fields should still be populated
━━ GROUP B: Boundary Conditions (6 scenarios) ━━


  # Why: Envelope version must follow the documented format
  @boundary
  Scenario: Version field accepts the current version string
    When I create a MessageEnvelope with version "1.0"
    Then the envelope should be valid

  # Why: source_id is the only truly required string field — verify empty is rejected
  @boundary @negative
  Scenario: Empty source_id is rejected
    When I create a MessageEnvelope with source_id ""
    Then it should raise a validation error
    And the error should indicate source_id must not be empty

  # Why: event_type must be a valid EventType enum member
  @boundary @negative
  Scenario: Invalid event_type is rejected
    When I create a MessageEnvelope with event_type "nonexistent_event"
    Then it should raise a validation error
    And the error should indicate the event type is not valid

  # Why: Optional fields should accept None gracefully
  @boundary
  Scenario Outline: Optional fields accept None
    When I create a MessageEnvelope with <field> set to None
    Then the envelope should be valid
    And <field> should be None

    Examples:
      | field          |
      | project        |
      | correlation_id |

  # Why: Payload is required — verify it works with an empty dict (minimal valid payload)
  @boundary
  Scenario: Envelope accepts an empty payload dictionary
    When I create a MessageEnvelope with an empty payload
    Then the envelope should be valid
    And the payload should be an empty dictionary

  # Why: message_id uniqueness is critical for deduplication across the fleet
  @boundary
  Scenario: Each envelope generates a unique message_id by default
    When I create 100 MessageEnvelopes without specifying message_id
    Then all 100 message_ids should be unique
━━ GROUP C: Negative Cases (4 scenarios) ━━


  # Why: Forward compatibility — unknown fields must be silently ignored (ADR XC-schema-versioning)
  @negative @smoke
  Scenario: Deserialising with unknown fields ignores them silently
    Given a JSON string with an extra field "future_field" set to "some_value"
    When I parse it as a MessageEnvelope
    Then it should parse without error
    And the unknown field should not appear in the model

  # Why: source_id is required — missing it must fail validation
  @negative
  Scenario: Missing required source_id raises a validation error
    Given a JSON string without a source_id field
    When I parse it as a MessageEnvelope
    Then it should raise a validation error
    And the error should mention source_id

  # Why: event_type is required — missing it must fail validation
  @negative
  Scenario: Missing required event_type raises a validation error
    Given a JSON string without an event_type field
    When I parse it as a MessageEnvelope
    Then it should raise a validation error
    And the error should mention event_type

  # Why: payload is required — missing it must fail validation
  @negative
  Scenario: Missing required payload raises a validation error
    Given a JSON string without a payload field
    When I parse it as a MessageEnvelope
    Then it should raise a validation error
    And the error should mention payload
━━ GROUP D: Edge Cases (4 scenarios) ━━


  # Why: Envelopes may carry large payloads — verify no silent truncation
  @edge-case
  Scenario: Envelope handles a large payload without truncation
    Given a payload dictionary with 50 keys and nested structures
    When I create and serialise a MessageEnvelope
    And then deserialise it back
    Then the round-tripped payload should match the original exactly

  # Why: Explicit overrides of defaults must be respected, not overwritten
  @edge-case
  Scenario: Explicit message_id and timestamp override defaults
    Given an explicit message_id "custom-id-12345" and timestamp "2026-01-15T10:30:00Z"
    When I create a MessageEnvelope with these values
    Then message_id should be "custom-id-12345"
    And timestamp should be "2026-01-15T10:30:00Z"

  # Why: Version field enables schema evolution — must round-trip faithfully
  @edge-case
  Scenario: Future version string round-trips correctly
    Given a MessageEnvelope with version "2.0"
    When I serialise and deserialise it
    Then version should be "2.0"

  # Why: Correlation chains may span many messages — verify the ID propagates unchanged
  @edge-case
  Scenario: Correlation ID propagates through a chain of messages
    Given a correlation_id "chain-001"
    When I create three envelopes each referencing correlation_id "chain-001"
    Then all three should have correlation_id "chain-001"
    And all three should have distinct message_ids
    And all three should have distinct timestamps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 19 scenarios across 4 groups
Inferred assumptions: 3 (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

[A] Accept  — include all scenarios as-is
[R] Reject  — exclude all scenarios in this group
[M] Modify  — accept but specify changes (provide inline)
[+] Add     — accept and add additional scenarios you describe
[?] Defer   — mark group for future specification; excluded from output

Fast path: type A A A A to accept all four groups at once.

GROUP A — Key Examples (5 scenarios): _
GROUP B — Boundary Conditions (6 scenarios): _
GROUP C — Negative Cases (4 scenarios): _
GROUP D — Edge Cases (4 scenarios): _

buildplan.md
A A A A
All four groups accepted. Proceeding to Phase 4.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've identified 4 additional scenarios covering data integrity and integration boundaries:

Data integrity (2):

Envelope with non-UTF-8-safe characters in payload values round-trips correctly
Concurrent creation of envelopes produces no message_id collisions
Integration boundaries (2):

Envelope with a payload containing datetime objects serialises them as ISO 8601 strings
Envelope deserialised from a different library version (extra fields + missing optional fields) parses successfully
Include them? [Y/S/N]:

Y
Including all 4 edge case scenarios. Proceeding to Phase 5.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION (3 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter to accept,
or type the actual value.

[1] source_id minimum length
Proposed: 1 character (non-empty)
Confidence: high
Basis: System spec requires source_id as a required field; empty string is meaningless as an identifier
Accept or enter value: _

[2] message_id format
Proposed: UUID v4 string (any valid UUID v4)
Confidence: high
Basis: System spec explicitly states default_factory=lambda: str(uuid4())
Accept or enter value: _

[3] payload type constraint
Proposed: dict[str, Any] — any JSON-serialisable dictionary
Confidence: high
Basis: System spec defines payload: dict[str, Any]; typed payloads are enforced at the event level, not the envelope level
Accept or enter value: _

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All 3 assumptions are high-confidence (derived directly from the system spec). Press Enter or type accept all to confirm all defaults, or respond per item.

accept all


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: Message Envelope
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
message-envelope.feature
message-envelope_assumptions.yaml
message-envelope_summary.md

Scenarios: 23 total
@key-example: 5   @boundary: 6
@negative: 4     @edge-case: 8
@smoke: 4       @regression: 0

Assumptions: 3 total
high: 3 (auto-proceed)
medium: 0
low: 0

Deferred: 0 scenario groups

Next steps:


Review: features/message-envelope/message-envelope.feature
Pass to feature-plan: /feature-plan "Message Envelope" \
  --context features/message-envelope/message-envelope_summary.md



/feature-spec "Event Type Schemas: typed payloads for pipeline, agent, jarvis, and fleet events" \
  --context docs/design/specs/nats-core-system-spec.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: Event Type Schemas
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Feature: Event Type Schemas
  As a fleet service developer
  I want typed payload schemas for every event in the system
  So that producers and consumers share a validated contract with no untyped dictionaries

  Background:
    Given the EventType enum and all payload schemas are available
━━ GROUP A: Key Examples (10 scenarios) ━━


  # Why: EventType enum is the central registry -- all documented event types must exist
  @key-example @smoke
  Scenario: EventType enum contains all documented event types
    When I inspect the EventType enum
    Then it should contain "feature_planned", "ready_for_dev", "build_started",
      "build_progress", "build_complete", "build_failed", "ticket_updated"
    And it should contain "status", "approval_request", "approval_response",
      "command", "result", "error"
    And it should contain "intent_classified", "dispatch", "agent_result", "notification"
    And it should contain "agent_register", "agent_deregister", "agent_heartbeat"

  # Why: Every EventType must map to a typed payload -- no orphan event types
  @key-example @smoke
  Scenario: Every event type has a corresponding payload class
    Given the EventType enum
    When I check each event type value
    Then there should be a Pydantic payload class for every EventType member

  # Why: EventType is a string enum -- values must be usable as plain strings in NATS messages
  @key-example
  Scenario: EventType values are plain strings
    When I use EventType.BUILD_STARTED as a string
    Then its value should be "build_started"

  # Why: Core pipeline event -- defines the shape of a feature planning announcement
  @key-example @smoke
  Scenario: Creating a valid FeaturePlannedPayload
    Given a feature_id "FEAT-AC1A" with 3 waves and 12 tasks
    When I create a FeaturePlannedPayload with valid fields
    Then feature_id should be "FEAT-AC1A"
    And wave_count should be 3
    And task_count should be 12
    And waves should contain 3 WaveSummary entries

  # Why: Build progress is the most frequently published pipeline event -- must validate bounds
  @key-example @smoke
  Scenario: Creating a valid BuildProgressPayload
    Given a build in progress at wave 2 of 4 with 55.0% overall progress
    When I create a BuildProgressPayload
    Then wave should be 2 and wave_total should be 4
    And overall_progress_pct should be 55.0

  # Why: Build completion is the terminal happy-path event -- must carry PR and summary data
  @key-example @smoke
  Scenario: Creating a valid BuildCompletePayload
    Given a completed build with 10 tasks completed, 0 failed, out of 10 total
    When I create a BuildCompletePayload
    Then tasks_completed should be 10
    And tasks_failed should be 0
    And tasks_total should be 10
    And pr_url should be present when a PR was created

  # Why: Approval flow is critical for human-in-the-loop -- request must carry risk context
  @key-example @smoke
  Scenario: Creating a valid ApprovalRequestPayload
    Given an agent "guardkit-factory" requesting approval for a destructive action
    When I create an ApprovalRequestPayload with risk_level "high"
    Then risk_level should be "high"
    And action_description should describe the action
    And timeout_seconds should default to 300

  # Why: Intent classification drives Jarvis routing -- confidence and target must be present
  @key-example @smoke
  Scenario: Creating a valid IntentClassifiedPayload
    Given user text "build the login page" classified as intent "software.build"
    When I create an IntentClassifiedPayload with confidence 0.92
    Then intent should be "software.build"
    And confidence should be 0.92
    And target_agent should identify the selected agent

  # Why: Fleet registration is the CAN bus pattern -- the manifest must declare capabilities
  @key-example @smoke
  Scenario: Creating a valid AgentRegistrationPayload
    Given an agent "product-owner-agent" with 2 intent capabilities
    When I create an AgentRegistrationPayload
    Then agent_id should be "product-owner-agent"
    And intents should contain 2 IntentCapability entries
    And each intent should have a pattern, signals, confidence, and description

  # Why: Dispatch is how Jarvis routes work to agents -- must carry correlation context
  @key-example
  Scenario: Creating a valid DispatchPayload
    Given an intent "ideate" dispatched to "ideation-agent"
    When I create a DispatchPayload with a correlation_id
    Then target_agent should be "ideation-agent"
    And intent should be "ideate"
    And correlation_id should link back to the original request
━━ GROUP B: Boundary Conditions (14 scenarios) ━━


  # Why: Build ID must follow the documented naming convention
  # [ASSUMPTION: confidence=high] build_id format is "build-{feature_id}-{YYYYMMDDHHMMSS}" per system spec
  @boundary @smoke
  Scenario: Build ID follows naming convention
    Given a feature_id "FEAT-AC1A"
    When I create a BuildProgressPayload with a valid build_id
    Then build_id should match the pattern "build-FEAT-AC1A-{YYYYMMDDHHMMSS}"

  # Why: Just-inside boundary -- progress at exactly 0.0 (start) and 100.0 (complete)
  @boundary
  Scenario Outline: Build progress percentage at valid bounds
    When I create a BuildProgressPayload with overall_progress_pct <value>
    Then the payload should be valid
    And overall_progress_pct should be <value>

    Examples:
      | value |
      | 0.0   |
      | 50.0  |
      | 100.0 |

  # Why: Just-outside boundary -- progress beyond 100 must be rejected
  @boundary @negative
  Scenario: Build progress percentage above 100 is rejected
    When I create a BuildProgressPayload with overall_progress_pct 100.1
    Then it should raise a validation error
    And the error should indicate the value must be at most 100.0

  # Why: Just-outside boundary -- negative progress must be rejected
  @boundary @negative
  Scenario: Build progress percentage below 0 is rejected
    When I create a BuildProgressPayload with overall_progress_pct -0.1
    Then it should raise a validation error
    And the error should indicate the value must be at least 0.0

  # Why: Intent confidence must be bounded 0.0-1.0 -- just-inside bounds
  @boundary
  Scenario Outline: Intent confidence at valid bounds
    When I create an IntentCapability with confidence <value>
    Then the capability should be valid

    Examples:
      | value |
      | 0.0   |
      | 0.5   |
      | 1.0   |

  # Why: Just-outside boundary -- confidence above 1.0 is nonsensical
  @boundary @negative
  Scenario: Intent confidence above 1.0 is rejected
    When I create an IntentCapability with confidence 1.01
    Then it should raise a validation error
    And the error should indicate confidence must be at most 1.0

  # Why: Just-outside boundary -- negative confidence is nonsensical
  @boundary @negative
  Scenario: Intent confidence below 0.0 is rejected
    When I create an IntentCapability with confidence -0.01
    Then it should raise a validation error
    And the error should indicate confidence must be at least 0.0

  # Why: IntentClassifiedPayload also has a confidence field -- same bounds apply
  @boundary @negative
  Scenario: IntentClassified confidence outside 0.0-1.0 is rejected
    When I create an IntentClassifiedPayload with confidence 1.5
    Then it should raise a validation error

  # Why: Agent status is a Literal type -- only documented values should be accepted
  @boundary
  Scenario Outline: Agent status accepts valid states
    When I create an AgentStatusPayload with state "<state>"
    Then the payload should be valid

    Examples:
      | state              |
      | running            |
      | idle               |
      | awaiting_approval  |
      | error              |
      | paused             |

  # Why: Approval risk_level is constrained -- only low/medium/high are valid
  @boundary
  Scenario Outline: Approval risk level accepts valid values
    When I create an ApprovalRequestPayload with risk_level "<level>"
    Then the payload should be valid

    Examples:
      | level  |
      | low    |
      | medium |
      | high   |

  # Why: Approval decision is constrained -- only documented values
  @boundary
  Scenario Outline: Approval decision accepts valid values
    When I create an ApprovalResponsePayload with decision "<decision>"
    Then the payload should be valid

    Examples:
      | decision |
      | approve  |
      | reject   |
      | defer    |
      | override |

  # Why: Heartbeat status is a Literal -- only documented values
  @boundary
  Scenario Outline: Heartbeat status accepts valid values
    When I create an AgentHeartbeatPayload with status "<status>"
    Then the payload should be valid

    Examples:
      | status   |
      | ready    |
      | busy     |
      | degraded |
      | draining |

  # Why: Registration status is a Literal -- only documented values
  @boundary
  Scenario Outline: Registration status accepts valid values
    When I create an AgentRegistrationPayload with status "<status>"
    Then the payload should be valid

    Examples:
      | status   |
      | ready    |
      | starting |
      | degraded |

  # Why: max_concurrent must be positive -- zero or negative means the agent cannot work
  # [ASSUMPTION: confidence=medium] max_concurrent minimum is 1 based on domain logic
  @boundary @negative
  Scenario: Agent max_concurrent of zero is rejected
    When I create an AgentRegistrationPayload with max_concurrent 0
    Then it should raise a validation error
    And the error should indicate max_concurrent must be at least 1
━━ GROUP C: Negative Cases (8 scenarios) ━━


  # Why: Invalid state string must fail validation -- not silently accepted
  @negative
  Scenario: Invalid agent status is rejected
    When I create an AgentStatusPayload with state "sleeping"
    Then it should raise a validation error
    And the error should indicate the state is not valid

  # Why: Invalid risk level must be caught at schema boundary
  @negative
  Scenario: Invalid approval risk level is rejected
    When I create an ApprovalRequestPayload with risk_level "critical"
    Then it should raise a validation error

  # Why: Invalid approval decision must be caught
  @negative
  Scenario: Invalid approval decision is rejected
    When I create an ApprovalResponsePayload with decision "ignore"
    Then it should raise a validation error

  # Why: Invalid heartbeat status must be caught
  @negative
  Scenario: Invalid heartbeat status is rejected
    When I create an AgentHeartbeatPayload with status "offline"
    Then it should raise a validation error

  # Why: Required fields must not be omittable on pipeline payloads
  @negative
  Scenario: FeaturePlannedPayload requires feature_id
    When I create a FeaturePlannedPayload without feature_id
    Then it should raise a validation error
    And the error should mention feature_id

  # Why: Required fields must not be omittable on build payloads
  @negative
  Scenario: BuildCompletePayload requires build_id
    When I create a BuildCompletePayload without build_id
    Then it should raise a validation error
    And the error should mention build_id

  # Why: Agent registration requires agent_id -- anonymous agents are not allowed
  @negative
  Scenario: AgentRegistrationPayload requires agent_id
    When I create an AgentRegistrationPayload without agent_id
    Then it should raise a validation error
    And the error should mention agent_id

  # Why: Dispatch requires a target agent -- routing with no destination is invalid
  @negative
  Scenario: DispatchPayload requires target_agent
    When I create a DispatchPayload without target_agent
    Then it should raise a validation error
    And the error should mention target_agent
━━ GROUP D: Edge Cases (8 scenarios) ━━


  # Why: Payloads should not use untyped dict at the top level -- enforces contract discipline
  @edge-case @smoke
  Scenario: Payload schemas use strict types not untyped dictionaries
    Given any payload class except generic error
    When I inspect its top-level fields
    Then no field should be an untyped dict[str, Any]
    # Nested dict is acceptable for extensible metadata only

  # Why: All payloads must survive JSON round-trip without data loss
  @edge-case @smoke
  Scenario Outline: Payload round-trips through JSON serialisation
    Given a valid <payload_class> with all fields populated
    When I serialise it to JSON and deserialise it back
    Then all field values should match the original

    Examples:
      | payload_class              |
      | FeaturePlannedPayload      |
      | BuildProgressPayload       |
      | BuildCompletePayload       |
      | BuildFailedPayload         |
      | AgentStatusPayload         |
      | ApprovalRequestPayload     |
      | ApprovalResponsePayload    |
      | IntentClassifiedPayload    |
      | DispatchPayload            |
      | AgentRegistrationPayload   |
      | AgentHeartbeatPayload      |
      | AgentDeregistrationPayload |

  # Why: Defaults must be applied for optional/defaulted fields when not supplied
  @edge-case
  Scenario: Default values are applied when fields are omitted
    When I create an ApprovalRequestPayload without specifying timeout_seconds
    Then timeout_seconds should be 300
    When I create an AgentRegistrationPayload without specifying max_concurrent
    Then max_concurrent should be 1
    When I create an AgentRegistrationPayload without specifying status
    Then status should be "ready"
    When I create an AgentDeregistrationPayload without specifying reason
    Then reason should be "shutdown"

  # Why: BuildFailedPayload must indicate whether the failure is recoverable
  @edge-case
  Scenario: Build failure indicates recoverability
    Given a build that failed due to a transient network error
    When I create a BuildFailedPayload with recoverable set to true
    Then recoverable should be true
    And failure_reason should describe the error

  # Why: WaveSummary and TaskProgress are nested models -- they must validate independently
  @edge-case
  Scenario: Nested models within pipeline payloads validate correctly
    Given a FeaturePlannedPayload with invalid data inside a WaveSummary
    When I attempt to create it
    Then it should raise a validation error pointing to the nested field

  # Why: Forward compatibility -- extra fields on payloads should be tolerated
  # [ASSUMPTION: confidence=high] Payloads use extra="ignore" per ADR XC-schema-versioning
  @edge-case
  Scenario: Payload schemas tolerate unknown fields for forward compatibility
    Given a JSON string for a BuildCompletePayload with an extra field "new_metric"
    When I parse it
    Then it should parse without error
    And the unknown field should be silently ignored

  # Why: IntentCapability is a nested model in registration -- must validate its own constraints
  @edge-case
  Scenario: IntentCapability validates independently within a registration
    Given an AgentRegistrationPayload with an IntentCapability missing its pattern field
    When I attempt to create it
    Then it should raise a validation error pointing to the IntentCapability

  # Why: Heartbeat queue_depth and active_tasks must not be negative
  # [ASSUMPTION: confidence=medium] queue_depth and active_tasks have ge=0 constraint
  @edge-case @boundary
  Scenario: Heartbeat rejects negative queue depth and active tasks
    When I create an AgentHeartbeatPayload with queue_depth -1
    Then it should raise a validation error
    When I create an AgentHeartbeatPayload with active_tasks -1
    Then it should raise a validation error
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 40 scenarios across 4 groups
Inferred assumptions: 5 (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

[A] Accept  — include all scenarios in this group as-is
[R] Reject  — exclude all scenarios in this group
[M] Modify  — accept but specify changes (provide inline)
[+] Add     — accept and add additional scenarios you describe
[?] Defer   — mark group for future specification; excluded from output

Fast path: type A A A A to accept all four groups at once.

Group	Scenarios	Your choice
GROUP A — Key Examples	10 scenarios	_
GROUP B — Boundary Conditions	14 scenarios	_
GROUP C — Negative Cases	8 scenarios	_
GROUP D — Edge Cases	8 scenarios	_
buildplan.md
A A A A
All four groups accepted. Moving to Phase 4.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've identified 6 additional scenarios covering security, concurrency, and integration boundaries:

Security (2):

Payload with excessively long string fields (potential DoS via validation)
Agent registration with a spoofed agent_id attempting to overwrite an existing registration
Concurrency (2):

Multiple BuildProgressPayloads for the same build_id with overlapping wave numbers
Two agents registering with the same agent_id simultaneously
Data Integrity (2):

BuildCompletePayload where tasks_completed + tasks_failed does not equal tasks_total
FeaturePlannedPayload where wave_count does not match the length of the waves list
Include them? [Y/S/N]:

Y
Included. Here are the 6 additional scenarios:


  # Why: Excessively long strings could cause performance issues during validation
  @edge-case
  Scenario: Payload rejects excessively long string fields
    When I create an AgentStatusPayload with task_description exceeding 10000 characters
    Then it should either raise a validation error or accept the value
    # [ASSUMPTION: confidence=low] No max_length constraint documented; behaviour is undefined

  # Why: Agent ID is the primary key in the registry -- spoofing must be detectable
  @edge-case
  Scenario: Agent registration payload validates agent_id format
    When I create an AgentRegistrationPayload with agent_id containing spaces and special characters
    Then it should raise a validation error
    # [ASSUMPTION: confidence=low] agent_id must be a kebab-case identifier

  # Why: Overlapping wave progress for the same build could confuse consumers
  @edge-case
  Scenario: BuildProgressPayload wave number must not exceed wave_total
    When I create a BuildProgressPayload with wave 5 and wave_total 3
    Then it should raise a validation error
    And the error should indicate wave must not exceed wave_total

  # Why: Duplicate agent_id registration is a fleet integrity concern
  @edge-case
  Scenario: Two registrations with the same agent_id are both valid payloads
    Given two AgentRegistrationPayloads with agent_id "ideation-agent"
    When I validate both payloads
    Then both should be valid
    # Conflict resolution is a routing concern, not a schema concern

  # Why: Inconsistent task counts would mislead dashboards and observers
  @edge-case
  Scenario: BuildCompletePayload task counts must be internally consistent
    When I create a BuildCompletePayload with tasks_completed 8, tasks_failed 1, tasks_total 10
    Then it should raise a validation error
    And the error should indicate completed plus failed must equal total
    # [ASSUMPTION: confidence=medium] Schema enforces tasks_completed + tasks_failed == tasks_total

  # Why: Mismatched wave_count and waves list length indicates a producer bug
  @edge-case
  Scenario: FeaturePlannedPayload wave_count must match waves list length
    Given a FeaturePlannedPayload with wave_count 3 but only 2 WaveSummary entries
    When I attempt to create it
    Then it should raise a validation error
    And the error should indicate wave_count must match the number of waves
    # [ASSUMPTION: confidence=medium] Schema enforces wave_count == len(waves)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION (8 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter to accept, or type the actual value.

#	Assumption	Proposed	Confidence	Basis
1	build_id format	build-{feature_id}-{YYYYMMDDHHMMSS}	high	System spec explicitly states this format
2	Payloads use extra="ignore" for forward compat	Yes	high	ADR XC-schema-versioning
3	max_concurrent minimum value	1	medium	Zero means agent cannot work; domain logic
4	queue_depth and active_tasks have ge=0 constraint	Yes	medium	Negative counts are nonsensical
5	tasks_completed + tasks_failed == tasks_total enforced in schema	Yes	medium	Inconsistency indicates producer bug
6	wave_count == len(waves) enforced in schema	Yes	medium	Mismatch indicates producer bug
7	Max string length on payload fields	No constraint	low	System spec does not define string limits
8	agent_id must be kebab-case identifier	Yes (pattern: ^[a-z][a-z0-9-]*$)	low	Convention from spec examples, not explicitly stated
Accept all, or type the number to override (e.g. 3: 0, 8: no constraint):

accept all
All assumptions confirmed. Generating output files.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: Event Type Schemas
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
event-type-schemas.feature
event-type-schemas_assumptions.yaml
event-type-schemas_summary.md

Scenarios: 46 total
@key-example: 10    @boundary: 14
@negative: 8        @edge-case: 14
@smoke: 10          @regression: 0

Assumptions: 8 total
high: 2 (auto-proceed)
medium: 4 (Coach review recommended)
low: 2 (human review required)

REVIEW REQUIRED: 2 low-confidence assumptions need verification
See: event-type-schemas_assumptions.yaml

Deferred: 0 scenario groups

Next steps:
Review: event-type-schemas.feature
Pass to feature-plan:


/feature-plan "Event Type Schemas" \
  --context features/event-type-schemas/event-type-schemas_summary.md




/feature-spec "Topic Registry: typed constants for all NATS subjects with resolution and project scoping" \
  --context docs/design/specs/nats-core-system-spec.md

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: Topic Registry
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: Topic Registry
As a fleet service developer
I want typed constants for all NATS subjects with resolution and project scoping
So that no service uses magic strings for topic names and all subjects are validated at import time

Background:
Given the Topics registry class is available

━━ GROUP A: Key Examples (8 scenarios) ━━

Why: Core pipeline topic resolution — most common operation in the fleet
@key-example @smoke
Scenario: Resolving a pipeline topic with a feature ID
When I resolve Topics.Pipeline.BUILD_STARTED with feature_id "FEAT-AC1A"
Then the result should be "pipeline.build-started.FEAT-AC1A"

Why: Agent status topic — used by every agent on every state change
@key-example @smoke
Scenario: Resolving an agent status topic with an agent ID
When I resolve Topics.Agents.STATUS with agent_id "guardkit-factory"
Then the result should be "agents.status.guardkit-factory"

Why: Fleet registration topic — no placeholders, used as-is
@key-example @smoke
Scenario: Fleet registration topic is a fixed string
When I access Topics.Fleet.REGISTER
Then the value should be "fleet.register"

Why: Jarvis dispatch — routes intent to a specific agent
@key-example @smoke
Scenario: Resolving a Jarvis dispatch topic with an agent name
When I resolve Topics.Jarvis.DISPATCH with agent "ideation-agent"
Then the result should be "jarvis.dispatch.ideation-agent"

Why: Project scoping is the multi-tenancy mechanism — critical path
@key-example @smoke
Scenario: Scoping a topic to a project
Given a resolved topic "pipeline.build-started.FEAT-001"
When I scope it to project "finproxy"
Then the result should be "finproxy.pipeline.build-started.FEAT-001"

Why: Wildcard topics enable fleet-wide subscriptions
@key-example
Scenario: Pipeline wildcard topic covers all pipeline events
When I access Topics.Pipeline.ALL
Then the value should be "pipeline.>"

Why: Agent tool invocation topic — used for request-reply RPC
@key-example
Scenario: Resolving an agent tool invocation topic
When I resolve Topics.Agents.TOOLS with agent_id "guardkit-factory" and tool_name "lint"
Then the result should be "agents.guardkit-factory.tools.lint"

Why: Approval topics use compound keys — agent + task
@key-example
Scenario: Resolving an approval request topic with agent and task IDs
When I resolve Topics.Agents.APPROVAL_REQUEST with agent_id "guardkit-factory" and task_id "TASK-001"
Then the result should be "agents.approval.guardkit-factory.TASK-001"

━━ GROUP B: Boundary Conditions (6 scenarios) ━━

Why: Just-inside boundary — single-character IDs must still resolve correctly
@boundary
Scenario: Resolving topics with minimal-length identifiers
When I resolve Topics.Pipeline.BUILD_STARTED with feature_id "X"
Then the result should be "pipeline.build-started.X"

Why: Just-inside boundary — IDs with hyphens and numbers are common in the fleet
@boundary
Scenario: Topic resolution handles IDs with hyphens and numbers
When I resolve Topics.Agents.STATUS with agent_id "my-agent-v2-01"
Then the result should be "agents.status.my-agent-v2-01"

Why: Wildcard topics must use valid NATS wildcard syntax
@boundary
Scenario Outline: All wildcard topics end with the NATS wildcard token
When I access <wildcard_topic>
Then the value should end with ">"


Examples:
  | wildcard_topic              |
  | Topics.Pipeline.ALL         |
  | Topics.Pipeline.ALL_BUILDS  |
  | Topics.Agents.STATUS_ALL    |
  | Topics.Agents.TOOLS_ALL     |
  | Topics.Fleet.HEARTBEAT_ALL  |
  | Topics.Fleet.ALL            |
Why: Just-outside boundary — empty feature_id produces invalid NATS subject
@boundary @negative
Scenario: Resolving a topic with an empty identifier is rejected
When I resolve Topics.Pipeline.BUILD_STARTED with feature_id ""
Then it should raise an error
And the error should indicate the identifier must not be empty

Why: Just-outside boundary — identifiers with dots would create incorrect subject hierarchy
@boundary @negative
Scenario: Resolving a topic with dots in the identifier is rejected
When I resolve Topics.Pipeline.BUILD_STARTED with feature_id "FEAT.001"
Then it should raise an error
And the error should indicate the identifier must not contain dots

Why: Just-outside boundary — identifiers with spaces are invalid NATS subjects
@boundary @negative
Scenario: Resolving a topic with spaces in the identifier is rejected
When I resolve Topics.Pipeline.BUILD_STARTED with feature_id "FEAT 001"
Then it should raise an error
And the error should indicate the identifier must not contain spaces

━━ GROUP C: Negative Cases (5 scenarios) ━━

Why: Missing template variables must fail explicitly, not produce partial subjects
@negative @smoke
Scenario: Resolving a template with a missing variable raises an error
When I resolve Topics.Pipeline.BUILD_STARTED without providing feature_id
Then it should raise an error
And the error should indicate the required variable is missing

Why: Extra template variables should be rejected to catch typos early
@negative
Scenario: Resolving a template with extra variables raises an error
When I resolve Topics.Pipeline.BUILD_STARTED with feature_id "FEAT-001" and unknown_var "X"
Then it should raise an error
And the error should indicate the variable is unexpected

Why: Empty project name would create a leading-dot subject
@negative
Scenario: Scoping to an empty project name is rejected
Given a resolved topic "pipeline.build-started.FEAT-001"
When I scope it to project ""
Then it should raise an error
And the error should indicate the project name must not be empty

Why: Project names with dots would collide with NATS subject hierarchy
@negative
Scenario: Scoping to a project name with dots is rejected
Given a resolved topic "pipeline.build-started.FEAT-001"
When I scope it to project "fin.proxy"
Then it should raise an error
And the error should indicate the project name must not contain dots

Why: Wildcard tokens in identifiers would create unintended subscriptions
@negative
Scenario: Identifiers containing NATS wildcards are rejected
When I resolve Topics.Agents.STATUS with agent_id "agent-*"
Then it should raise an error
And the error should indicate the identifier must not contain wildcard tokens

━━ GROUP D: Edge Cases (8 scenarios) ━━

Why: Pipeline topics and EventType enum must stay synchronised
@edge-case @smoke
Scenario: Every pipeline topic template corresponds to an EventType
Given the Topics.Pipeline class
When I collect all non-wildcard topic templates
Then every topic should correspond to a value in the EventType enum

Why: Agent topic templates and EventType enum must stay synchronised
@edge-case @smoke
Scenario: Every agent topic template corresponds to an EventType
Given the Topics.Agents class
When I collect all non-wildcard, non-tool topic templates
Then every topic should correspond to a value in the EventType enum

Why: No magic strings — all topic usage must go through the registry
@edge-case
Scenario: No hardcoded topic strings exist outside the registry
Given the fleet codebase
When I search for hardcoded topic string patterns like "pipeline.build-" or "agents.status."
Then no file outside topics.py should contain hardcoded topic strings

Why: Resolve and for_project must compose correctly
@edge-case
Scenario: Resolving and then project-scoping a topic produces the correct subject
When I resolve Topics.Pipeline.BUILD_COMPLETE with feature_id "FEAT-001"
And then scope the result to project "guardkit"
Then the result should be "guardkit.pipeline.build-complete.FEAT-001"

Why: Project-scoped wildcard subscriptions are valid for project-filtered monitoring
@edge-case
Scenario: Project-scoping a wildcard topic produces a valid scoped wildcard
When I scope Topics.Pipeline.ALL to project "finproxy"
Then the result should be "finproxy.pipeline.>"

Why: All topic templates must produce valid NATS subjects when resolved
@edge-case
Scenario Outline: All resolved topics are valid NATS subjects
When I resolve <topic_template> with valid placeholder values
Then the result should contain only alphanumeric characters, hyphens, dots, and greater-than signs
And the result should not contain consecutive dots
And the result should not start or end with a dot


Examples:
  | topic_template                  |
  | Topics.Pipeline.FEATURE_PLANNED |
  | Topics.Pipeline.BUILD_STARTED   |
  | Topics.Pipeline.BUILD_COMPLETE  |
  | Topics.Agents.STATUS            |
  | Topics.Agents.APPROVAL_REQUEST  |
  | Topics.Agents.COMMAND           |
  | Topics.Agents.TOOLS             |
  | Topics.Fleet.HEARTBEAT          |
  | Topics.Jarvis.COMMAND           |
  | Topics.Jarvis.DISPATCH          |
  | Topics.System.HEALTH            |
Why: Topic constants should be accessible as class attributes without instantiation
@edge-case
Scenario: Topics class does not require instantiation
When I access Topics.Pipeline.BUILD_STARTED directly as a class attribute
Then it should return the topic template string
And no Topics object needs to be created

Why: Approval response topic must be the request topic with ".response" suffix
@edge-case
Scenario: Approval response topic extends the request topic
When I resolve Topics.Agents.APPROVAL_REQUEST with agent_id "factory" and task_id "T1"
And I resolve Topics.Agents.APPROVAL_RESPONSE with agent_id "factory" and task_id "T1"
Then the response topic should be the request topic with ".response" appended

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 27 scenarios across 4 groups
Inferred assumptions: 5 (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

[A] Accept  — include all scenarios in this group as-is
[R] Reject  — exclude all scenarios in this group
[M] Modify  — accept but specify changes (provide inline)
[+] Add     — accept and add additional scenarios you describe
[?] Defer   — mark group for future specification; excluded from output

Fast path: type "A A A A" to accept all four groups at once.

GROUP A — Key Examples (8 scenarios): _
GROUP B — Boundary Conditions (6 scenarios): _
GROUP C — Negative Cases (5 scenarios): _
GROUP D — Edge Cases (8 scenarios): _

buildplan.md
A A A A
All four groups accepted. Proceeding to Phase 4.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've identified 5 additional scenarios covering security and integration boundaries:

Security (2):

Identifier containing NATS subject injection characters (e.g., newlines, null bytes)
Project name containing shell metacharacters passed through to subjects
Integration boundaries (3):

Topic template constants are immutable at runtime (no accidental reassignment)
All five namespace classes (Pipeline, Agents, Fleet, Jarvis, System) are present
Resolve method is idempotent — resolving the same template twice yields identical results
Include them? [Y/S/N]:

Y
Included. Here are the 5 additional scenarios that will be added to the output:

Why: Newlines or null bytes in identifiers could corrupt NATS protocol framing
@edge-case @negative
Scenario: Identifiers containing control characters are rejected
When I resolve Topics.Agents.STATUS with agent_id containing a newline character
Then it should raise an error
And the error should indicate the identifier contains invalid characters

Why: Shell metacharacters in project names must not pass through to subjects
@edge-case @negative
Scenario: Project name with shell metacharacters is rejected
When I scope a topic to project "fin;rm -rf"
Then it should raise an error
And the error should indicate the project name contains invalid characters

Why: Topic constants must not be accidentally overwritten at runtime
@edge-case
Scenario: Topic template constants are immutable class attributes
When I attempt to reassign Topics.Pipeline.BUILD_STARTED to a different value
Then the assignment should be prevented or the original value should be unchanged

Why: All documented namespaces must be present — missing one means lost coverage
@edge-case @smoke
Scenario: All five namespace classes are present in the registry
When I inspect the Topics class
Then it should contain Pipeline, Agents, Fleet, Jarvis, and System namespaces

Why: Idempotency — same inputs must always produce same output
@edge-case
Scenario: Resolving the same template twice yields identical results
When I resolve Topics.Pipeline.BUILD_STARTED with feature_id "FEAT-001" twice
Then both results should be identical

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION (5 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter to accept,
or type the actual value.

[1] Identifier validation — dots rejected
Proposed: Identifiers (feature_id, agent_id, etc.) must not contain dots
Confidence: medium
Basis: Dots are NATS subject delimiters; dots in identifiers would create unintended hierarchy levels
Accept or enter value: _

[2] Identifier validation — spaces rejected
Proposed: Identifiers must not contain spaces
Confidence: high
Basis: NATS subjects do not permit spaces per protocol specification
Accept or enter value: _

[3] Identifier validation — empty rejected
Proposed: Empty string identifiers are rejected by resolve()
Confidence: high
Basis: Empty segments produce consecutive dots ("pipeline.build-started.") which are invalid NATS subjects
Accept or enter value: _

[4] Identifier validation — wildcards rejected
Proposed: Identifiers must not contain * or > characters
Confidence: high
Basis: These are NATS wildcard tokens; allowing them in identifiers would create unintended subscriptions
Accept or enter value: _

[5] Project name validation
Proposed: Project names follow same rules as identifiers (no dots, spaces, wildcards, or empty)
Confidence: medium
Basis: Project names are prepended to subjects via {project}.{topic}, so the same constraints apply
Accept or enter value: _

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

accept all
All assumptions confirmed. Generating output files.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: Topic Registry
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
topic-registry.feature
topic-registry_assumptions.yaml
topic-registry_summary.md

Scenarios: 32 total
@key-example: 8    @boundary: 6
@negative: 5       @edge-case: 13
@smoke: 8          @regression: 0

Assumptions: 5 total
high: 3 (auto-proceed)
medium: 2 (Coach review recommended)
low: 0

Deferred: 0 scenario groups

Next steps:
Review: topic-registry.feature
Pass to feature-plan:
/feature-plan "Topic Registry" --context features/topic-registry/topic-registry_summary.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━






/feature-spec "NATS Configuration: pydantic-settings for connection management" \
  --context docs/design/specs/nats-core-system-spec.md


Context loaded: stack=python, 0 src models (library not yet scaffolded), 3 existing .feature files
(message-envelope, event-type-schemas, topic-registry), system spec Feature 5 provides NATSConfig schema
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: NATS Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Feature: NATS Configuration
  As a fleet service developer
  I want connection settings managed via pydantic-settings with environment variable overrides
  So that every service configures its NATS connection consistently without hardcoded values

  Background:
    Given the NATSConfig settings class is available
━━ GROUP A: Key Examples (5 scenarios) ━━


  # Why: Most common case -- zero-config local development
  @key-example @smoke
  Scenario: Default configuration connects to localhost
    Given no NATS-related environment variables are set
    When I create a NATSConfig with no arguments
    Then url should be "nats://localhost:4222"
    And connect_timeout should be 5.0
    And reconnect_time_wait should be 2.0
    And max_reconnect_attempts should be 60
    And name should be "nats-core-client"

  # Why: Primary deployment override -- all services read NATS_URL from env
  @key-example @smoke
  Scenario: Environment variable overrides the default URL
    Given NATS_URL is set to "nats://gb10.tail:4222"
    When I create a NATSConfig
    Then url should be "nats://gb10.tail:4222"

  # Why: Account-based auth for multi-tenant NATS -- user/password from env
  @key-example
  Scenario: Configuring user and password authentication from environment
    Given NATS_USER is set to "appmilla"
    And NATS_PASSWORD is set to "s3cret"
    When I create a NATSConfig
    Then user should be "appmilla"
    And password should be "s3cret"

  # Why: NKey credentials for production -- more secure than user/password
  @key-example
  Scenario: Configuring NKey credentials file from environment
    Given NATS_CREDS_FILE is set to "/etc/nats/appmilla.creds"
    When I create a NATSConfig
    Then creds_file should be "/etc/nats/appmilla.creds"

  # Why: Explicit constructor overrides -- used in tests and one-off scripts
  @key-example
  Scenario: Constructor arguments override defaults
    When I create a NATSConfig with url "nats://test:4222" and connect_timeout 1.0
    Then url should be "nats://test:4222"
    And connect_timeout should be 1.0
    And all other fields should retain their defaults
━━ GROUP B: Boundary Conditions (6 scenarios) ━━


  # Why: Just-inside boundary -- connect_timeout must be non-negative
  @boundary
  Scenario: Connect timeout at zero is accepted
    When I create a NATSConfig with connect_timeout 0.0
    Then connect_timeout should be 0.0

  # Why: Just-outside boundary -- negative timeout is meaningless
  @boundary @negative
  Scenario: Negative connect timeout is rejected
    When I create a NATSConfig with connect_timeout -1.0
    Then it should raise a validation error
    And the error should indicate connect_timeout must be non-negative

  # Why: Just-inside boundary -- reconnect time wait must be non-negative
  @boundary
  Scenario: Reconnect time wait at zero is accepted
    When I create a NATSConfig with reconnect_time_wait 0.0
    Then reconnect_time_wait should be 0.0

  # Why: Just-outside boundary -- negative reconnect wait is meaningless
  @boundary @negative
  Scenario: Negative reconnect time wait is rejected
    When I create a NATSConfig with reconnect_time_wait -1.0
    Then it should raise a validation error
    And the error should indicate reconnect_time_wait must be non-negative

  # Why: Just-inside boundary -- max reconnect attempts must be non-negative
  @boundary
  Scenario: Max reconnect attempts at zero means no retries
    When I create a NATSConfig with max_reconnect_attempts 0
    Then max_reconnect_attempts should be 0

  # Why: Just-outside boundary -- negative retry count is meaningless
  @boundary @negative
  Scenario: Negative max reconnect attempts is rejected
    When I create a NATSConfig with max_reconnect_attempts -1
    Then it should raise a validation error
    And the error should indicate max_reconnect_attempts must be non-negative
━━ GROUP C: Negative Cases (4 scenarios) ━━


  # Why: URL must be a valid NATS URI -- reject garbage input at config time
  # [ASSUMPTION: confidence=medium] URL must start with nats:// or tls:// per nats-py convention
  @negative
  Scenario: Invalid URL scheme is rejected
    When I create a NATSConfig with url "http://localhost:4222"
    Then it should raise a validation error
    And the error should indicate the URL scheme must be nats or tls

  # Why: Empty URL is never valid -- catch misconfigured environments early
  @negative
  Scenario: Empty URL is rejected
    When I create a NATSConfig with url ""
    Then it should raise a validation error
    And the error should indicate the URL must not be empty

  # Why: Client name must not be empty -- NATS monitoring relies on it
  # [ASSUMPTION: confidence=medium] Client name is required for observability in NATS dashboard
  @negative
  Scenario: Empty client name is rejected
    When I create a NATSConfig with name ""
    Then it should raise a validation error
    And the error should indicate the client name must not be empty

  # Why: Partial auth config is a misconfiguration -- catch it early
  # [ASSUMPTION: confidence=low] Providing user without password (or vice versa) should be an error
  @negative
  Scenario: User without password is rejected
    Given NATS_USER is set to "appmilla"
    And NATS_PASSWORD is not set
    When I create a NATSConfig
    Then it should raise a validation error
    And the error should indicate both user and password must be provided together
━━ GROUP D: Edge Cases (4 scenarios) ━━


  # Why: Environment variables take precedence over constructor defaults but not explicit args
  @edge-case
  Scenario: Environment variable precedence over defaults
    Given NATS_URL is set to "nats://env-server:4222"
    When I create a NATSConfig with no arguments
    Then url should be "nats://env-server:4222"

  # Why: Multiple config instances should be independent -- no shared mutable state
  @edge-case
  Scenario: Multiple NATSConfig instances are independent
    Given NATS_URL is set to "nats://shared:4222"
    When I create two NATSConfig instances
    And I modify the url on the first instance
    Then the second instance url should still be "nats://shared:4222"

  # Why: .env file support is a pydantic-settings feature -- verify it works
  # [ASSUMPTION: confidence=medium] NATSConfig reads from .env files via pydantic-settings default behaviour
  @edge-case
  Scenario: Configuration loads from dotenv file
    Given a .env file containing NATS_URL="nats://dotenv-server:4222"
    When I create a NATSConfig
    Then url should be "nats://dotenv-server:4222"

  # Why: Config should be serialisable for logging/debugging without leaking secrets
  # [ASSUMPTION: confidence=low] Password and creds_file should be excluded from repr/str output
  @edge-case
  Scenario: Sensitive fields are masked in string representation
    Given a NATSConfig with user "admin" and password "s3cret"
    When I convert the config to a string representation
    Then the password should be masked or excluded
    And the user should be visible
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 19 scenarios across 4 groups
Inferred assumptions: 5 (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

[A] Accept  — include all scenarios in this group as-is
[R] Reject  — exclude all scenarios in this group
[M] Modify  — accept but specify changes (provide inline)
[+] Add     — accept and add additional scenarios you describe
[?] Defer   — mark group for future specification; excluded from output

Fast path: type A A A A to accept all four groups at once.

GROUP A — Key Examples (5 scenarios): _
GROUP B — Boundary Conditions (6 scenarios): _
GROUP C — Negative Cases (4 scenarios): _
GROUP D — Edge Cases (4 scenarios): _
buildplan.md
A A A A
All four groups accepted. Moving to Phase 4.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've identified 4 additional scenarios covering security and integration boundaries:

Security (2):

Password/creds_file values not leaked when config is logged or serialised to dict
Creds file path traversal (e.g., ../../etc/passwd) is rejected or normalised
Integration boundaries (2):

Config produces a valid kwargs dict consumable by nats-py Client.connect()
Config with both password auth and creds_file specified — which takes precedence?
Include them? [Y/S/N]:

Y
Noted. Here are the 4 additional scenarios for curation:

━━ EDGE CASE EXPANSION: Security & Integration (4 scenarios) ━━


  # Why: Configs get logged in production -- secrets must not leak into log output
  @edge-case
  Scenario: Password is not exposed when config is serialised to dict
    Given a NATSConfig with user "admin" and password "s3cret"
    When I serialise the config to a dictionary
    Then the password value should be masked as "**********" or excluded entirely

  # Why: Creds file path should be validated to prevent directory traversal
  @edge-case @negative
  Scenario: Creds file with path traversal is rejected
    When I create a NATSConfig with creds_file "../../etc/passwd"
    Then it should raise a validation error
    And the error should indicate the credentials path is invalid

  # Why: NATSConfig must produce kwargs that nats-py Client.connect() accepts directly
  @edge-case
  Scenario: Config produces valid nats-py connection kwargs
    Given a NATSConfig with url "nats://gb10.tail:4222" and connect_timeout 10.0
    When I convert the config to connection kwargs
    Then the result should contain servers as a list with "nats://gb10.tail:4222"
    And the result should contain connect_timeout as 10.0
    And the result should be accepted by nats-py connect

  # Why: Ambiguous auth config -- user/password and creds_file are mutually exclusive
  # [ASSUMPTION: confidence=low] Providing both password auth and creds_file is a misconfiguration
  @edge-case @negative
  Scenario: Providing both password auth and creds file is rejected
    Given NATS_USER is set to "admin"
    And NATS_PASSWORD is set to "s3cret"
    And NATS_CREDS_FILE is set to "/etc/nats/appmilla.creds"
    When I create a NATSConfig
    Then it should raise a validation error
    And the error should indicate that password auth and credentials file are mutually exclusive
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Curation for these 4 scenarios — [A] Accept / [R] Reject / [M] Modify / [?] Defer:

EXPANSION — Security & Integration (4 scenarios): _
A
All expansion scenarios accepted. Moving to Phase 5.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION (6 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter to accept, or type the actual value/decision.

[1] Valid URL schemes
Proposed: nats:// and tls://  Confidence: medium  Basis: nats-py convention; nats:// for plaintext, tls:// for TLS
Accept or enter value: _

[2] Client name must not be empty
Proposed: Reject empty string  Confidence: medium  Basis: NATS monitoring dashboard uses client name for identification
Accept or enter value: _

[3] User and password must be provided together
Proposed: Reject user-without-password and password-without-user  Confidence: low  Basis: Partial auth credentials are likely a misconfiguration; nats-py requires both
Accept or enter value: _

[4] .env file support
Proposed: NATSConfig reads .env files via pydantic-settings default  Confidence: medium  Basis: pydantic-settings BaseSettings supports env_file in SettingsConfigDict
Accept or enter value: _

[5] Sensitive fields masked in repr/serialisation
Proposed: password and creds_file masked in __repr__/__str__ and model_dump()  Confidence: low  Basis: Security best practice; prevents accidental secret logging
Accept or enter value: _

[6] Password auth and creds file are mutually exclusive
Proposed: Reject config that provides both user/password AND creds_file  Confidence: low  Basis: Ambiguous auth intent; nats-py uses one or the other
Accept or enter value: _

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

accept
All 6 assumptions confirmed. Generating output files.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: NATS Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
nats-configuration.feature
nats-configuration_assumptions.yaml
nats-configuration_summary.md

Scenarios: 23 total
@key-example: 5    @boundary: 6
@negative: 8      @edge-case: 8
@smoke: 2        @regression: 0

Assumptions: 6 total
high: 0 (auto-proceed)
medium: 3 (Coach review recommended)
low: 3 (all confirmed by human)

Deferred: 0 scenario groups

Next steps:
Review: nats-configuration.feature
Pass to feature-plan:


/feature-plan "NATS Configuration" --context features/nats-configuration/nats-configuration_summary.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━









/feature-spec "NATS Client: typed publish/subscribe wrapper with automatic envelope handling" \
  --context docs/design/specs/nats-core-system-spec.md


Context loaded: stack=python, 4 existing .feature files (envelope, events, topics, config),
system spec read (Feature 4: NATS Client section + fleet convenience methods), no pyproject.toml yet
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: NATS Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Feature: NATS Client
  As a fleet service developer
  I want a typed publish/subscribe wrapper with automatic envelope handling
  So that services can exchange strongly-typed events without manual serialisation or topic string construction

  Background:
    Given a NATSClient configured with default settings
    And the NATS connection is established
━━ GROUP A: Key Examples (8 scenarios) ━━


  # Why: Core publish path -- typed event is wrapped in envelope and sent to the correct topic
  @key-example @smoke
  Scenario: Publishing a typed event wraps it in a MessageEnvelope
    When I publish a BuildCompletePayload for feature "FEAT-001"
    Then the client should publish to "pipeline.build-complete.FEAT-001"
    And the message should be a valid JSON-serialised MessageEnvelope
    And the envelope source_id should identify the publisher
    And the envelope event_type should be BUILD_COMPLETE
    And the envelope payload should contain the BuildCompletePayload fields

  # Why: Core subscribe path -- incoming messages are deserialised into typed envelopes
  @key-example @smoke
  Scenario: Subscribing with a typed handler receives deserialised envelopes
    Given I subscribe to build complete events for feature "FEAT-001"
    When a BUILD_COMPLETE message arrives on the corresponding topic
    Then the handler should receive a deserialised MessageEnvelope
    And the envelope payload should be parseable as BuildCompletePayload

  # Why: Multi-tenancy -- project-scoped publish prefixes topics and sets envelope project field
  @key-example @smoke
  Scenario: Project-scoped publish prefixes the topic
    When I publish a BuildCompletePayload for feature "FEAT-001" with project "finproxy"
    Then the topic should be "finproxy.pipeline.build-complete.FEAT-001"
    And the envelope project field should be "finproxy"

  # Why: Correlation -- publish must propagate correlation_id for request chains
  @key-example
  Scenario: Publishing with a correlation ID includes it in the envelope
    When I publish a BuildCompletePayload with correlation_id "session-abc-123"
    Then the envelope correlation_id should be "session-abc-123"
    And the envelope message_id should be a distinct value

  # Why: Fleet registration -- agent self-announces on startup via convenience method
  @key-example @smoke
  Scenario: Registering an agent publishes to the fleet register topic
    Given an AgentRegistrationPayload for agent "product-owner-agent"
    When I call register_agent with the payload
    Then the client should publish to "fleet.register"
    And the envelope event_type should be AGENT_REGISTER
    And the payload should include the agent's declared intent capabilities

  # Why: Fleet heartbeat -- periodic liveness signal via convenience method
  @key-example
  Scenario: Sending a heartbeat publishes to the agent-specific heartbeat topic
    Given an AgentHeartbeatPayload for agent "ideation-agent"
    When I call heartbeat with the payload
    Then the client should publish to "fleet.heartbeat.ideation-agent"
    And the envelope event_type should be AGENT_HEARTBEAT

  # Why: Fleet deregistration -- graceful shutdown via convenience method
  @key-example
  Scenario: Deregistering an agent publishes to the fleet deregister topic
    When I call deregister_agent with agent_id "youtube-planner" and reason "shutdown"
    Then the client should publish to "fleet.deregister"
    And the envelope event_type should be AGENT_DEREGISTER
    And the payload reason should be "shutdown"

  # Why: Agent-to-agent tool invocation -- request-reply pattern for remote tool calls
  @key-example
  Scenario: Calling a remote agent tool uses request-reply
    When I call call_agent_tool with agent_id "guardkit-factory" and tool_name "lint"
    Then the client should publish a request to "agents.guardkit-factory.tools.lint"
    And it should await a reply from the target agent
━━ GROUP B: Boundary Conditions (6 scenarios) ━━


  # Why: Just-inside boundary -- empty payload dict is valid (minimal event)
  @boundary
  Scenario: Publishing with an empty payload dictionary succeeds
    Given an event type that accepts an empty payload
    When I publish the event with an empty payload
    Then the publish should succeed
    And the envelope payload should be an empty dictionary

  # Why: Just-inside boundary -- single-character source_id is the minimum valid identifier
  @boundary
  Scenario: Client with a single-character source ID publishes successfully
    Given a NATSClient with source_id "x"
    When I publish any typed event
    Then the envelope source_id should be "x"

  # Why: Just-outside boundary -- empty source_id must be rejected at client creation
  @boundary @negative
  Scenario: Creating a client with an empty source ID is rejected
    When I create a NATSClient with source_id ""
    Then it should raise a validation error
    And the error should indicate source_id must not be empty

  # Why: Just-inside boundary -- subscribing to a wildcard topic captures all matching subjects
  @boundary
  Scenario: Subscribing to a wildcard topic receives messages from all matching subjects
    Given I subscribe to all pipeline events using the wildcard topic
    When messages arrive on "pipeline.build-started.FEAT-001" and "pipeline.build-complete.FEAT-002"
    Then the handler should receive both messages as deserialised envelopes

  # Why: Just-inside boundary -- topic with maximum segment depth resolves correctly
  # [ASSUMPTION: confidence=medium] Approval topics have the deepest nesting: agents.approval.{agent_id}.{task_id}.response
  @boundary
  Scenario: Deeply nested topic template resolves correctly
    When I resolve the approval response topic with agent_id "jarvis" and task_id "task-99"
    Then the resolved topic should be "agents.approval.jarvis.task-99.response"

  # Why: Just-outside boundary -- missing template variables must raise an error, not produce partial topics
  @boundary @negative
  Scenario: Publishing with missing topic template variables is rejected
    When I attempt to publish to a topic template without providing all required variables
    Then it should raise an error
    And the error should indicate the missing template variable
━━ GROUP C: Negative Cases (6 scenarios) ━━


  # Why: Publishing on a disconnected client must fail clearly, not silently drop messages
  @negative @smoke
  Scenario: Publishing on a disconnected client raises an error
    Given a NATSClient that is not connected
    When I attempt to publish a typed event
    Then it should raise a connection error
    And the error should indicate the client is not connected

  # Why: Subscribing on a disconnected client must fail, not appear to succeed silently
  @negative
  Scenario: Subscribing on a disconnected client raises an error
    Given a NATSClient that is not connected
    When I attempt to subscribe to a topic
    Then it should raise a connection error

  # Why: Malformed incoming messages must not crash the subscriber
  @negative
  Scenario: Receiving invalid JSON on a subscribed topic does not crash the handler
    Given I subscribe to build complete events for feature "FEAT-001"
    When a message with invalid JSON arrives on the topic
    Then the handler should not crash
    And the malformed message should be reported as an error

  # Why: Incoming message with wrong event type must be handled gracefully
  @negative
  Scenario: Receiving an envelope with an unexpected event type is handled gracefully
    Given I subscribe to build complete events for feature "FEAT-001"
    When an envelope with event_type BUILD_FAILED arrives on the topic
    Then the handler should not crash
    And the unexpected event should be reported or ignored

  # Why: Request-reply timeout -- tool call to an unresponsive agent must not hang indefinitely
  # [ASSUMPTION: confidence=medium] Tool call timeout defaults to 30 seconds per common RPC convention
  @negative
  Scenario: Agent tool call times out when no reply is received
    When I call call_agent_tool with agent_id "offline-agent" and tool_name "test"
    And no reply arrives within the timeout period
    Then the call should raise a timeout error
    And the error should indicate the target agent did not respond

  # Why: Double-connect must not silently create multiple connections
  @negative
  Scenario: Connecting an already-connected client raises an error or is idempotent
    Given a NATSClient that is already connected
    When I call connect again
    Then it should either raise an error or be safely idempotent
    And there should not be duplicate underlying connections
━━ GROUP D: Edge Cases (7 scenarios) ━━


  # Why: Connection resilience -- transient NATS outages must not crash the client permanently
  @edge-case @smoke
  Scenario: Client reconnects automatically after a transient disconnection
    Given a connected NATSClient
    When the NATS server becomes temporarily unavailable
    And then becomes available again
    Then the client should reconnect automatically
    And previously registered subscriptions should resume receiving messages

  # Why: Graceful shutdown -- subscriptions must be drained before disconnect to avoid message loss
  @edge-case @smoke
  Scenario: Graceful disconnect drains all active subscriptions
    Given a connected NATSClient with active subscriptions
    When I call disconnect
    Then all subscriptions should be drained before the connection closes
    And the connection should close cleanly
    And no in-flight messages should be lost

  # Why: Concurrent publishes -- the client must be safe for use from multiple async tasks
  @edge-case
  Scenario: Concurrent publishes from multiple tasks do not corrupt messages
    Given a connected NATSClient
    When I publish 50 events concurrently from separate async tasks
    Then all 50 messages should arrive at the NATS server
    And each message should be a valid MessageEnvelope
    And no messages should be interleaved or corrupted

  # Why: Multiple subscriptions to the same topic -- both handlers must receive messages
  @edge-case
  Scenario: Multiple handlers on the same topic all receive the message
    Given two handlers subscribed to the same topic
    When a message arrives on that topic
    Then both handlers should receive the deserialised envelope

  # Why: Fleet registry read -- the KV-backed registry must return all registered agents
  @edge-case
  Scenario: Reading the fleet registry returns all registered agents
    Given three agents have registered via register_agent
    When I call get_fleet_registry
    Then the result should contain all three agents keyed by agent_id
    And each entry should be a valid AgentRegistrationPayload

  # Why: Fleet watcher -- watch_fleet must deliver registration and deregistration events in real time
  @edge-case
  Scenario: Watching the fleet receives registration and deregistration events
    Given I am watching the fleet via watch_fleet
    When an agent registers and then deregisters
    Then the watcher callback should receive the registration event
    And then the deregistration event in order

  # Why: Envelope defaults must be populated by the client, not by the caller
  @edge-case
  Scenario: Published envelope has auto-generated message_id and timestamp
    When I publish any typed event without specifying message_id or timestamp
    Then the published envelope should contain a valid UUID v4 message_id
    And the timestamp should be within 1 second of now in UTC
    And the version should be "1.0"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 27 scenarios across 4 groups
Inferred assumptions: 4 (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

[A] Accept  — include all scenarios in this group as-is
[R] Reject  — exclude all scenarios in this group
[M] Modify  — accept but specify changes (provide inline)
[+] Add     — accept and add additional scenarios you describe
[?] Defer   — mark group for future specification; excluded from output

Fast path: type A A A A to accept all four groups at once.

Group	Scenarios	Your choice
GROUP A — Key Examples	8 scenarios	_
GROUP B — Boundary Conditions	6 scenarios	_
GROUP C — Negative Cases	6 scenarios	_
GROUP D — Edge Cases	7 scenarios	_
buildplan.md
A A A A
All four groups accepted. Moving to Phase 4.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've identified 6 additional scenarios:

Security (2):

Payload injection — publishing an envelope where payload contains fields that collide with envelope-level fields (e.g., a nested source_id)
Subscription to topics with user-controlled segments — ensuring injected wildcards in agent_id don't escalate subscription scope
Concurrency (2):

Simultaneous register and deregister for the same agent — KV state must be consistent
Publishing during reconnection — messages queued while disconnected should be delivered or fail cleanly
Integration boundaries (2):

NATS server returns a slow consumer warning — client should handle backpressure without crashing
KV bucket unavailable when reading fleet registry — should fail with a clear error, not hang
Include them? [Y/S/N]:

Y
Here are the 6 additional scenarios:

━━ EDGE CASE EXPANSION: Security (2) ━━


  # Why: Payload must not be able to override envelope-level fields during serialisation
  @edge-case
  Scenario: Payload containing envelope-level field names does not override the envelope
    Given a payload dictionary containing a key "source_id" with value "attacker"
    When I publish the event with source_id "legitimate-agent"
    Then the envelope source_id should be "legitimate-agent"
    And the payload "source_id" key should remain in the payload only

  # Why: User-controlled topic segments must not inject NATS wildcards that widen subscription scope
  @edge-case @negative
  Scenario: Topic resolution rejects wildcard characters in segment values
    When I attempt to publish with agent_id "evil.>" or feature_id "FEAT.*"
    Then it should raise a validation error
    And the error should indicate that wildcard characters are not allowed in topic segment values
━━ EDGE CASE EXPANSION: Concurrency (2) ━━


  # Why: Simultaneous register and deregister must not leave KV in an inconsistent state
  @edge-case
  Scenario: Simultaneous registration and deregistration for the same agent resolves consistently
    When register_agent and deregister_agent are called concurrently for agent "flaky-agent"
    Then the fleet registry should contain either the agent or not
    And the KV state should be consistent with the last operation that completed

  # Why: Messages published during a reconnection window must not be silently dropped
  @edge-case
  Scenario: Publishing during reconnection either queues or fails clearly
    Given a connected NATSClient
    When the NATS server disconnects and the client is reconnecting
    And I attempt to publish a typed event during the reconnection window
    Then the publish should either queue the message for delivery after reconnection
    Or raise a clear error indicating the connection is not yet restored
━━ EDGE CASE EXPANSION: Integration Boundaries (2) ━━


  # Why: Slow consumer warnings from NATS must not crash the client
  @edge-case
  Scenario: Client handles slow consumer backpressure without crashing
    Given a connected NATSClient with a subscription
    When the NATS server signals slow consumer backpressure
    Then the client should not crash
    And it should report the backpressure condition as a warning

  # Why: KV bucket unavailability must fail with a clear error, not hang indefinitely
  @edge-case @negative
  Scenario: Fleet registry read fails clearly when KV bucket is unavailable
    Given the agent-registry KV bucket is not available
    When I call get_fleet_registry
    Then it should raise an error indicating the registry is unavailable
    And the call should not hang indefinitely
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These 6 scenarios use the same curation actions. [A/R/M/+/?]:

A
All 6 accepted. Moving to Phase 5.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION (4 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter to accept,
or type the actual value.

#	Assumption	Proposed	Confidence	Basis
1	Deepest topic nesting depth	agents.approval.{agent_id}.{task_id}.response (5 segments)	medium	Derived from Topics registry in system spec
2	Tool call request-reply timeout	30 seconds	medium	Common RPC convention; nats-py default request timeout
3	URL validation scheme must be nats:// or tls://	nats:// or tls:// only	medium	nats-py convention; already specified in nats-configuration.feature
4	Partial auth (user without password) is an error	Yes — both must be provided together	low	Already specified in nats-configuration.feature; applies to client creation too
Accept all defaults, or provide overrides per item:

accept all
All accepted. Generating output files.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: NATS Client
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
nats-client.feature
nats-client_assumptions.yaml
nats-client_summary.md

Scenarios: 33 total
@key-example: 8    @boundary: 6
@negative: 6       @edge-case: 13
@smoke: 6          @regression: 0

Assumptions: 4 total
high: 0 (auto-proceed)
medium: 3 (Coach review recommended)
low: 1 (confirmed by human)

Deferred: 0 scenario groups

Next steps:
Review: nats-client.feature
Pass to feature-plan:
/feature-plan "NATS Client" --context features/nats-client/nats-client_summary.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━











/feature-spec "Fleet Registration: CAN bus agent discovery with KV-backed routing table" \
  --context docs/design/specs/nats-core-system-spec.md \
  --context docs/design/decisions/ADR-004-dynamic-fleet-registration.md


Context loaded: stack=python, 5 existing .feature files, 1 ADR (ADR-004: dynamic fleet registration),
system spec Feature 6 with 10 BDD scenarios, 4 fleet payload schemas (Registration, Heartbeat,
Deregistration, IntentCapability), KV bucket "agent-registry", Topics.Fleet namespace
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: Fleet Registration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Feature: Fleet Registration
  As a fleet operator
  I want agents to self-announce their capabilities on startup and maintain liveness via heartbeats
  So that the router can dynamically discover agents and build a KV-backed routing table without code changes
Background:
Given the NATS connection is established
And the "agent-registry" KV bucket exists

━━ GROUP A: Key Examples (6 scenarios) ━━

A1. Agent registers on startup


# Why: Core registration path — agent publishes its capability manifest and appears in the routing table
@key-example @smoke
Scenario: Agent registers on startup
  Given the Product Owner Agent is starting
  When it publishes an AgentRegistrationPayload to fleet.register
  Then the agent should appear in the "agent-registry" KV bucket with key "product-owner-agent"
  And the registration should include agent_id "product-owner-agent"
  And it should declare at least one intent capability
  And each declared intent should have a confidence score between 0.0 and 1.0
A2. Registration includes signal words for intent matching


# Why: Signal words are the basis for Jarvis intent classification — they must be present and meaningful
@key-example
Scenario: Registration includes signal words for intent matching
  Given the Ideation Agent registers with the fleet
  Then its registration should declare intent "ideate" with signals including "explore" and "brainstorm"
  And the intent "ideate" should have confidence of at least 0.8
A3. Agent begins heartbeating after registration


# Why: Heartbeats are the liveness mechanism — registration without heartbeating is incomplete
@key-example @smoke
Scenario: Agent begins heartbeating after registration
  Given the Ideation Agent has registered with the fleet
  When 30 seconds elapse
  Then the agent should have published a heartbeat to "fleet.heartbeat.ideation-agent"
  And the heartbeat should include current queue_depth and active_tasks
  And status should be one of "ready", "busy", "degraded", or "draining"
A4. Graceful deregistration removes agent from routing table


# Why: Clean shutdown path — agents that exit gracefully should be removed immediately, not wait for timeout
@key-example @smoke
Scenario: Graceful deregistration removes agent from routing table
  Given "youtube-planner" is registered in the fleet
  When it publishes an AgentDeregistrationPayload with reason "shutdown"
  Then "youtube-planner" should be removed from the "agent-registry" KV bucket
  And the router should no longer dispatch requests to "youtube-planner"
A5. New agent auto-discovered without router changes


# Why: The core CAN bus value proposition — zero router code changes when the fleet grows
@key-example
Scenario: New agent is auto-discovered without router changes
  Given the router is running with 3 registered agents
  When a new agent "product-owner-agent" publishes a registration to fleet.register
  Then the router should add it to the routing table
  And no code changes to the router were required
A6. Registration survives router restart via KV persistence


# Why: KV-backed routing table is the key persistence guarantee from ADR-004
@key-example
Scenario: Registration survives router restart via KV persistence
  Given 5 agents are registered in the "agent-registry" KV bucket
  When the router restarts
  Then all 5 agents should be available in the routing table from KV
  And no agents needed to re-register
━━ GROUP B: Boundary Conditions (6 scenarios) ━━

B1. Confidence score at exact boundaries


# Why: Confidence 0.0 and 1.0 are valid edge values — both must be accepted
@boundary
Scenario Outline: Confidence score at valid boundaries is accepted
  Given an agent registers with intent "general" at confidence <confidence>
  When the registration is processed
  Then the registration should succeed

  Examples:
    | confidence |
    | 0.0        |
    | 0.5        |
    | 1.0        |
B2. Confidence score outside valid range


# Why: Confidence must be strictly within [0.0, 1.0] — values outside should be rejected at validation
@boundary @negative
Scenario Outline: Confidence score outside valid range is rejected
  Given an agent registers with intent "general" at confidence <confidence>
  When the registration is validated
  Then the registration should be rejected
  And the error should indicate confidence must be between 0.0 and 1.0

  Examples:
    | confidence |
    | -0.1       |
    | 1.1        |
B3. Max concurrent at boundaries


# Why: max_concurrent controls concurrency gating — zero is meaningless and should be rejected
@boundary
Scenario: Agent registers with max_concurrent of 1
  Given an agent registers with max_concurrent 1
  When the registration is processed
  Then the registration should succeed
  And the agent should accept at most 1 concurrent task

# [ASSUMPTION: confidence=medium] max_concurrent minimum is 1 based on domain logic (0 = useless agent)
@boundary @negative
Scenario: Agent registers with max_concurrent of 0
  Given an agent registers with max_concurrent 0
  When the registration is validated
  Then the registration should be rejected
  And the error should indicate max_concurrent must be at least 1
B4. Heartbeat timeout at exact boundary


# [ASSUMPTION: confidence=high] Heartbeat timeout is 90s (3× the 30s interval) per system spec
@boundary
Scenario: Heartbeat received at exactly 89 seconds does not trigger timeout
  Given a registered agent with its last heartbeat 89 seconds ago
  When the router checks liveness
  Then the agent should still be marked as available

@boundary
Scenario: No heartbeat for exactly 90 seconds triggers timeout
  Given a registered agent with its last heartbeat 90 seconds ago
  When the router checks liveness
  Then the agent should be marked as unavailable
B5. Agent with zero intents declared


# Why: An agent with no declared intents cannot receive any routed requests — should this be rejected?
# [ASSUMPTION: confidence=medium] Agents must declare at least one intent capability
@boundary @negative
Scenario: Agent registration with no intent capabilities is rejected
  Given an agent registers with an empty intents list
  When the registration is validated
  Then the registration should be rejected
  And the error should indicate at least one intent capability is required
B6. Queue depth at zero


# Why: Queue depth 0 is the normal idle state — must be accepted and used as tiebreaker
@boundary
Scenario: Heartbeat with queue depth of zero is valid
  Given a registered agent publishes a heartbeat with queue_depth 0
  When the heartbeat is processed
  Then the agent should be recorded with queue_depth 0
  And the agent should be preferred over agents with higher queue depth for tiebreaking
━━ GROUP C: Negative Cases (5 scenarios) ━━

C1. Registration with missing required fields


# Why: agent_id and name are required — missing them should fail at the schema level
@negative
Scenario Outline: Registration missing required field is rejected
  Given an AgentRegistrationPayload without <field>
  When the registration is validated
  Then the registration should be rejected
  And the error should indicate <field> is required

  Examples:
    | field    |
    | agent_id |
    | name     |
    | template |
C2. Duplicate agent_id registration


# Why: Re-registration should update, not duplicate — the KV key is agent_id
@negative
Scenario: Re-registration with the same agent_id updates the existing entry
  Given "ideation-agent" is already registered in the fleet
  When a new registration for "ideation-agent" arrives with updated intents
  Then the routing table should contain only one entry for "ideation-agent"
  And the entry should reflect the updated intents
C3. Deregistration for an unknown agent


# Why: Deregistering a non-existent agent should be idempotent, not an error
@negative
Scenario: Deregistration for an unknown agent is silently ignored
  Given "phantom-agent" is not registered in the fleet
  When a deregistration for "phantom-agent" is received
  Then no error should be raised
  And the routing table should be unchanged
C4. Heartbeat from an unregistered agent


# Why: Race condition where heartbeat arrives before registration (or after deregistration)
# [ASSUMPTION: confidence=medium] Heartbeats from unregistered agents are ignored without error
@negative
Scenario: Heartbeat from an unregistered agent is ignored
  Given "ghost-agent" is not registered in the fleet
  When a heartbeat from "ghost-agent" is received
  Then no error should be raised
  And "ghost-agent" should not appear in the routing table
C5. Routing when no agent matches the intent


# Why: Must handle the case where no registered agent can fulfil a request
@negative
Scenario: Request with no matching agent intent is not dispatched
  Given registered agents only handle intents "ideate" and "software.build"
  When a request with intent "translate.document" arrives
  Then the request should not be dispatched
  And the requestor should be informed that no capable agent is available
━━ GROUP D: Edge Cases (5 scenarios) ━━

D1. Confidence-based routing selects best agent


# Why: Core routing logic — highest confidence wins
@edge-case
Scenario: Confidence-based routing selects the best agent
  Given "ideation-agent" declares intent "ideate" with confidence 0.9
  And "general-purpose-agent" declares intent "ideate" with confidence 0.3
  When a request with intent "ideate" arrives
  Then the router should dispatch to "ideation-agent"
D2. Queue-aware routing for tied confidence


# Why: When confidence is equal, queue depth is the tiebreaker per ADR-004
@edge-case
Scenario: Queue-aware routing breaks confidence ties
  Given "factory-1" declares "software.build" with confidence 1.0 and queue_depth 3
  And "factory-2" declares "software.build" with confidence 1.0 and queue_depth 0
  When a new "software.build" request arrives
  Then the router should dispatch to "factory-2"
D3. Concurrent task limit prevents overloading


# Why: max_concurrent is the backpressure mechanism — full agents must not receive more work
@edge-case
Scenario: Agent at max_concurrent capacity is skipped for routing
  Given "guardkit-factory" registers with max_concurrent 2 and active_tasks 2
  And "guardkit-factory-2" registers with max_concurrent 2 and active_tasks 0
  When a new "software.build" request arrives
  Then the router should dispatch to "guardkit-factory-2"
  And "guardkit-factory" should not receive the request
D4. Heartbeat timeout marks agent unavailable


# Why: Liveness detection is the safety net — crashed agents must be removed from routing
@edge-case
Scenario: Heartbeat timeout marks agent unavailable
  Given "architect-agent" is registered and was heartbeating every 30 seconds
  When no heartbeat is received for 90 seconds
  Then the router should mark "architect-agent" as unavailable
  And "architect-agent" should not receive new dispatches
D5. Agent recovers from unavailable state by re-heartbeating


# Why: Transient failures should be self-healing — a recovered agent should rejoin the fleet
# [ASSUMPTION: confidence=medium] An agent that resumes heartbeating after timeout automatically returns to available
@edge-case
Scenario: Agent recovers from unavailable state by resuming heartbeats
  Given "architect-agent" has been marked unavailable due to heartbeat timeout
  When a new heartbeat from "architect-agent" is received
  Then "architect-agent" should be marked as available again
  And it should be eligible for routing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 22 scenarios across 4 groups
Inferred assumptions: 6 (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

[A] Accept  — include all scenarios in this group as-is
[R] Reject  — exclude all scenarios in this group
[M] Modify  — accept but specify changes (provide inline)
[+] Add     — accept and add additional scenarios you describe
[?] Defer   — mark group for future specification; excluded from output

Fast path: type A A A A to accept all four groups at once.

GROUP A — Key Examples (6 scenarios): _
GROUP B — Boundary Conditions (6 scenarios): _
GROUP C — Negative Cases (5 scenarios): _
GROUP D — Edge Cases (5 scenarios): _

buildplan.md
A A A A
All four groups accepted. Proceeding to Phase 4.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGE CASE EXPANSION (optional)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

I've identified 6 additional scenarios covering security, concurrency, and integration boundaries:

Security (2):

Agent registration with a spoofed agent_id that collides with a trusted agent
Registration payload with excessively large metadata attempting resource exhaustion
Concurrency (2):

Two agents register with the same agent_id simultaneously (race condition on KV write)
Heartbeat and deregistration arrive at the same instant for the same agent
Integration boundaries (2):

KV bucket unavailable when registration arrives (NATS KV down, JetStream degraded)
Router receives a dispatch request while the fleet registry is empty
Include them? [Y/S/N]:

Y
Here are the 6 additional scenarios:

━━ GROUP E: Security (2 scenarios) ━━

E1. Spoofed agent_id collision


# Why: A rogue agent could try to overwrite a trusted agent's registration by using its agent_id
# [ASSUMPTION: confidence=low] No authentication mechanism on registration — any agent can claim any agent_id
@edge-case @security
Scenario: Re-registration with an existing agent_id overwrites the previous entry
  Given "product-owner-agent" is registered with intent "product.document" at confidence 0.9
  When a new registration arrives claiming agent_id "product-owner-agent" with different intents
  Then the routing table should reflect the new registration
  And the previous capabilities should be replaced
E2. Excessively large metadata in registration


# Why: Unbounded metadata dict could exhaust KV storage or memory
# [ASSUMPTION: confidence=medium] Maximum metadata size is 64KB based on NATS KV value size conventions
@edge-case @security
Scenario: Registration with excessively large metadata is rejected
  Given an AgentRegistrationPayload with metadata exceeding 64KB
  When the registration is validated
  Then the registration should be rejected
  And the error should indicate metadata exceeds the maximum allowed size
━━ GROUP F: Concurrency (2 scenarios) ━━

F1. Simultaneous registration with the same agent_id


# Why: Two instances starting at the same time could race on the KV write — last-write-wins is acceptable
@edge-case @concurrency
Scenario: Simultaneous registrations with the same agent_id resolve to last-write-wins
  Given two instances of "guardkit-factory" publish registrations simultaneously
  When both registrations are processed
  Then the routing table should contain exactly one entry for "guardkit-factory"
  And the entry should reflect whichever registration was processed last
F2. Heartbeat and deregistration arrive simultaneously


# Why: Race between a heartbeat in-flight and a deregistration — deregistration should take precedence
@edge-case @concurrency
Scenario: Deregistration takes precedence over a concurrent heartbeat
  Given "ideation-agent" is registered and heartbeating
  When a deregistration and a heartbeat for "ideation-agent" arrive simultaneously
  Then "ideation-agent" should be removed from the routing table
  And the heartbeat should not resurrect the agent
━━ GROUP G: Integration Boundaries (2 scenarios) ━━

G1. KV bucket unavailable during registration


# Why: JetStream or the KV bucket could be temporarily degraded — registration must handle this gracefully
@edge-case @integration
Scenario: Registration fails gracefully when KV bucket is unavailable
  Given the "agent-registry" KV bucket is unavailable
  When an agent publishes a registration to fleet.register
  Then the registration should fail with a retriable error
  And the agent should be able to retry registration when KV recovers
G2. Dispatch request when fleet registry is empty


# Why: Cold start or total fleet failure — router must not crash when no agents are registered
@edge-case @integration
Scenario: Dispatch request with an empty fleet registry returns no capable agent
  Given no agents are registered in the fleet
  When a request with intent "software.build" arrives
  Then the request should not be dispatched
  And the requestor should be informed that no agents are available
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Curate these groups using the same [A/R/M/+/?] actions:

GROUP E — Security (2 scenarios): _
GROUP F — Concurrency (2 scenarios): _
GROUP G — Integration Boundaries (2 scenarios): _

A
All three expansion groups accepted. Proceeding to Phase 5.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ASSUMPTION RESOLUTION (8 items)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each assumption has a proposed default. Press Enter to accept, or type the actual value.

[1] Heartbeat interval
Proposed: 30 seconds  Confidence: high  Basis: System spec states "periodic heartbeat every 30s"
Accept or enter value: _

[2] Heartbeat timeout (marks agent unavailable)
Proposed: 90 seconds (3× interval)  Confidence: high  Basis: System spec states "If no heartbeat for 90s"
Accept or enter value: _

[3] Minimum max_concurrent value
Proposed: 1  Confidence: medium  Basis: max_concurrent=0 would mean the agent can never receive work
Accept or enter value: _

[4] Minimum intent capabilities per registration
Proposed: 1 (at least one intent required)  Confidence: medium  Basis: Agent with no intents is unroutable
Accept or enter value: _

[5] Heartbeats from unregistered agents
Proposed: Silently ignored  Confidence: medium  Basis: Defensive handling of race conditions
Accept or enter value: _

[6] Agent recovery after heartbeat timeout
Proposed: Automatic — resuming heartbeats restores availability  Confidence: medium  Basis: Self-healing fleet without manual intervention
Accept or enter value: _

[7] Registration authentication
Proposed: None — any agent can claim any agent_id  Confidence: low  Basis: No auth mechanism described in spec or ADR-004; CAN bus pattern is trust-based within the network
Accept or enter value: _

[8] Maximum metadata size per registration
Proposed: 64KB  Confidence: medium  Basis: NATS KV default max value size; prevents resource exhaustion
Accept or enter value: _

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

accept all
All assumptions confirmed. Proceeding to Phase 6 — writing output files.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: Fleet Registration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
fleet-registration.feature
fleet-registration_assumptions.yaml
fleet-registration_summary.md

Scenarios: 28 total
@key-example: 6   @boundary: 6
@negative: 5      @edge-case: 11
@smoke: 3         @regression: 0

Assumptions: 8 total
high: 2 (auto-proceed)
medium: 5 (Coach review recommended)
low: 1 (human review required)

REVIEW REQUIRED: 1 low-confidence assumption needs verification
ASSUM-007: No auth on registration (trust-based CAN bus pattern)
See: fleet-registration_assumptions.yaml

Deferred: 0 scenario groups

Next steps:
Review: fleet-registration.feature
Pass to feature-plan:


/feature-plan "Fleet Registration" \
  --context features/fleet-registration/fleet-registration_summary.md



━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: FEAT-2637 — Message Envelope
Review: TASK-40B8 (completed)

Created: tasks/backlog/message-envelope/


├── README.md
├── IMPLEMENTATION-GUIDE.md (2 waves, Mermaid diagrams)
├── TASK-ME01-project-scaffolding.md      (scaffolding, wave 1, complexity 3)
├── TASK-ME02-message-envelope-model.md   (declarative, wave 2, complexity 4)
└── TASK-ME03-message-envelope-tests.md   (testing, wave 2, complexity 4)
Execution Strategy:

Wave	Tasks	Parallel?
1	TASK-ME01: Project scaffolding	Solo
2	TASK-ME02: EventType + MessageEnvelope, TASK-ME03: Test suite (23 scenarios)	Yes
Feature file: .guardkit/features/FEAT-2637.yaml

Next steps:

Review: IMPLEMENTATION-GUIDE.md
Start Wave 1: /task-work TASK-ME01
Then Wave 2: /task-work TASK-ME02 and /task-work TASK-ME03
Or use AutoBuild: /feature-build FEAT-2637

GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-2637 --verbose --max-turns 30




━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: Event Type Schemas — FEAT-310F

Structure created: tasks/backlog/event-type-schemas/


tasks/backlog/event-type-schemas/
├── README.md
├── IMPLEMENTATION-GUIDE.md  (data flow + integration contract + dependency diagrams)
├── TASK-ETS1-pipeline-event-payloads.md    (complexity: 5, wave 1)
├── TASK-ETS2-agent-event-payloads.md       (complexity: 3, wave 1)
├── TASK-ETS3-jarvis-event-payloads.md      (complexity: 3, wave 1)
├── TASK-ETS4-fleet-event-payloads.md       (complexity: 5, wave 1)
└── TASK-ETS5-dispatcher-and-tests.md       (complexity: 5, wave 2)
Execution plan:

Wave 1: TASK-ETS1, ETS2, ETS3, ETS4 in parallel (all independent)
Wave 2: TASK-ETS5 (dispatcher + 46 BDD tests) after Wave 1 complete
Key decisions baked in:

ASSUM-008: kebab-case agent_id enforced via Field(pattern=...) on AgentManifest and AgentDeregistrationPayload
ASSUM-007: no max_length on strings (accepted per spec)
AgentRegistrationPayload → implemented as AgentManifest (DDR-002)
All cross-field validators (wave <= wave_total, completed + failed == total, len(waves) == wave_count) go in TASK-ETS1
Seam tests included in TASK-ETS5 to validate dispatcher registry contracts from each domain task
Feature file: .guardkit/features/FEAT-310F.yaml


# Start implementation
/task-work TASK-ETS1   # (+ ETS2, ETS3, ETS4 in parallel)
/task-work TASK-ETS5   # after Wave 1 complete

# AutoBuild
/feature-build FEAT-310F

GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-310F --verbose --max-turns 30






━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING COMPLETE: Topic Registry
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature ID: FEAT-DCBD
Approach: Nested class-based registry (Topics outer class, 5 inner namespaces)
Complexity: 4/10 | Estimated effort: ~2.5 hours

Files created:


tasks/backlog/topic-registry/
├── README.md
├── IMPLEMENTATION-GUIDE.md      ← data flow diagram, §4 integration contract, risk table
├── TASK-TR01-implement-topics-module.md    (declarative, Wave 1)
└── TASK-TR02-test-suite-topics.md          (testing, Wave 2)
tasks/backlog/TASK-TR00-plan-topic-registry.md
.guardkit/features/FEAT-DCBD.yaml
Execution:


Wave 1: TASK-TR01 — implement src/nats_core/topics.py
Wave 2: TASK-TR02 — test_topics.py (32 BDD scenarios) — after TR01
Next steps:


/task-work TASK-TR01   # implement topics.py
/task-work TASK-TR02   # test suite
# or:
/feature-build FEAT-DCBD

GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-DCBD --verbose --max-turns 30




━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE PLANNING COMPLETE — NATS Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: FEAT-DD0E
Module: src/nats_core/config.py
Approach: pydantic-settings BaseSettings (Option 1)
Review task: TASK-F7AE (completed)

Tasks created in tasks/backlog/nats-configuration/:

Wave	Task	Title	Type	Complexity
1	TASK-A3EB	Scaffold NATSConfig module	scaffolding	2
2	TASK-A500	Core connection fields + URL validator	declarative	3
3	TASK-83F5	Auth fields + mutual exclusivity	feature	4
4	TASK-B725	to_connect_kwargs() + secret masking	feature	3
5	TASK-132C	Test suite (all 23 BDD scenarios)	testing	3
Guides:

IMPLEMENTATION-GUIDE.md — data flow diagram, architecture notes, BDD coverage matrix
README.md — feature overview
AutoBuild ready:


/feature-build FEAT-DD0E
Or work tasks manually:


/task-work TASK-A3EB

GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-DD0E --verbose --max-turns 30




━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Feature FEAT-3845 created — 9 tasks across 4 execution waves

Feature structure:


tasks/backlog/nats-client/
├── README.md
├── IMPLEMENTATION-GUIDE.md
├── TASK-NC01-natsconfig-agentconfig-models.md       (declarative, wave 1)
├── TASK-NC02-topics-registry.md                     (declarative, wave 1)
├── TASK-NC03-event-payload-models.md                (declarative, wave 2)
├── TASK-NC04-agentmanifest-registry.md              (declarative, wave 3)
├── TASK-NC05-natsclient-core.md                     (feature, wave 4)
├── TASK-NC06-fleet-methods-kv-registry.md           (feature, wave 5)
├── TASK-NC07-call-agent-tool.md                     (feature, wave 5)
├── TASK-NC08-unit-tests.md                          (testing, wave 6)
└── TASK-NC09-integration-tests.md                   (testing, wave 6)
Execution waves (as resolved by AutoBuild):

Wave 1: NC01, NC02, NC03 (parallel — NC03 after ME02)
Wave 2: NC04, NC05 (parallel — each after their respective deps)
Wave 3: NC06, NC07, NC08 (parallel)
Wave 4: NC09 (integration tests — all code complete)
📁 Feature file: .guardkit/features/FEAT-3845.yaml

Next steps:

Ensure message-envelope feature (TASK-ME01-03) is complete first
Start implementation: /task-work TASK-NC01 and /task-work TASK-NC02 in parallel
AutoBuild: /feature-build FEAT-3845


GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-3845 --verbose --max-turns 30






━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Feature: FEAT-BEA5 — Fleet Registration

Task	Title	Type	Complexity	Wave
TASK-FR-001	Scaffolding	scaffolding	2	1
TASK-FR-002	Pydantic models	declarative	4	2
TASK-FR-003	ManifestRegistry ABC + InMemory	feature	4	3
TASK-FR-004	NATSKVManifestRegistry	feature	6	4 ‖
TASK-FR-005	Heartbeat monitor + routing	feature	6	4 ‖
TASK-FR-006	Test suite (28 BDD)	testing	4	5
Parallel execution groups: 5 waves (TASK-FR-004 and TASK-FR-005 run in parallel in Wave 4)

Artefacts:

tasks/backlog/fleet-registration/IMPLEMENTATION-GUIDE.md — data flow, integration contracts, Mermaid diagrams
.guardkit/features/FEAT-BEA5.yaml — AutoBuild feature file
Next steps:


# AutoBuild (recommended)
/feature-build FEAT-BEA5

# Or manual, start with Wave 1
/task-work TASK-FR-001


Phase 2-4: Review Analysis, Synthesis, and Report


=========================================================================
REVIEW REPORT: TASK-7448
Review forge-v2-alignment tasks for correctness and regression safety
=========================================================================

Mode:     Architectural
Depth:    Standard
Score:    78/100
Findings: 9
Recommendations: 7
Verdict:  PROCEED WITH MODIFICATIONS
=========================================================================
Executive Summary
The two implementation tasks (TASK-NCFA-001 and TASK-NCFA-002) are fundamentally sound — the payloads, topics, and deprecation strategy are the correct approach for Forge v2.2 alignment. However, the review identified 3 issues that must be addressed before implementation and 4 issues that should be addressed. None are blocking enough to warrant a "revise significantly" or "block" decision.

Section 1: Payload Design Correctness — Score: 7/10
Finding 1 (MEDIUM): correlation_id design divergence — intentional but underdocumented
MessageEnvelope already has correlation_id: str | None as an optional field (envelope.py:150-152). The new payloads add correlation_id: str as a required field on each payload model.

This is intentional — the payload-level correlation_id threads build lifecycle events together (domain concern), while the envelope-level one links request-response pairs (infrastructure concern). This is the correct design, but the tasks should document this dual-level correlation to avoid future confusion.

Risk: Low. Implementer may ask "why is this duplicated?" — answer should be in the code comments.

Finding 2 (HIGH): ConfigDict(extra='allow') inconsistency across new payloads
All 8 existing pipeline payloads use ConfigDict(extra="ignore") per ADR-002 (_pipeline.py:29). TASK-NCFA-001 specifies extra='allow' for BuildQueuedPayload only (from Appendix C), but the four sketch payloads in IMPLEMENTATION-GUIDE.md don't specify a ConfigDict at all.

This creates an inconsistency: BuildQueuedPayload is forward-compatible with unknown fields while BuildPausedPayload, BuildResumedPayload, StageCompletePayload, and StageGatedPayload silently drop unknown fields. If a future publisher adds fields to any of these, consumers running current code will lose that data.

Recommendation: Make a conscious decision — either all five new payloads use extra='allow' (if forward-compat is the v2.2 strategy) or all use extra='ignore' (if consistency with ADR-002 is paramount). Update both TASK-NCFA-001 and IMPLEMENTATION-GUIDE.md accordingly.

Finding 3 (LOW): Sketch payload style inconsistencies
The IMPLEMENTATION-GUIDE.md sketches use:

Optional[float] instead of float | None (the codebase convention per Python 3.10+)
datetime fields (paused_at, resumed_at, etc.) — new to this module, requires from datetime import datetime import
No Field(description=...) annotations (required by CLAUDE.md conventions)
No explicit ConfigDict (should be specified)
These are style issues that will be caught during implementation but are worth noting for the implementer.

Finding 4 (LOW): TriggerSource / OriginatingAdapter placement
These Literal types are pipeline-specific. Keeping them in _pipeline.py is correct. No action needed.

Section 2: Topic Naming and Registry — Score: 9/10
Finding 5 (PASS): Topic naming patterns are correct
All six new topics follow the established {domain}.{event-name}.{parameter} pattern perfectly:

pipeline.build-queued.{feature_id} — matches pipeline.build-started.{feature_id}
pipeline.stage-complete.{feature_id} — new "stage" segment, correctly distinguished from "build"
agents.command.broadcast — static topic, no placeholder
Finding 6 (INFO): Wildcard ALL_BUILDS won't catch stage events
Topics.Pipeline.ALL_BUILDS = "pipeline.build-*.>" (topics.py:86) matches build-queued, build-paused, build-resumed but not stage-complete or stage-gated. This is correct behavior — stages are not builds. The catch-all Topics.Pipeline.ALL = "pipeline.>" (topics.py:85) covers everything.

No action needed, but TASK-NCFA-001 could add a ALL_STAGES = "pipeline.stage-*.>" convenience constant if stage-level subscriptions are anticipated.

Finding 7 (PASS): agents.command.broadcast — no conflict
agents.command.> subscribers will receive broadcast messages. This is the intended behavior. Targeted subscribers using agents.command.{specific_agent_id} won't receive broadcasts. No conflict.

Section 3: Deprecation Strategy — Score: 6/10
Finding 8 (HIGH): Deprecation warning mechanism must be __init__, NOT module-level import
The IMPLEMENTATION-GUIDE.md suggests warnings.warn(...) in __init_subclass__ or on module import. Both are wrong:

__init_subclass__ fires when a class inherits from FeaturePlannedPayload, not when it's instantiated. Nobody subclasses it.
Module-level import would fire every time nats_core is imported, because envelope.py:36 imports FeaturePlannedPayload at the top level. This would produce a deprecation warning on every single from nats_core import ... call.
Correct approach: Override __init__ or use Pydantic's model_post_init to emit the warning only on instantiation:


def model_post_init(self, __context: Any) -> None:
    warnings.warn(
        "FeaturePlannedPayload is deprecated; use BuildQueuedPayload",
        DeprecationWarning,
        stacklevel=2,
    )
Recommendation: Update IMPLEMENTATION-GUIDE.md and TASK-NCFA-001 to specify model_post_init as the deprecation mechanism.

Finding 9 (MEDIUM): Existing tests will need pytest.warns wrappers
After adding the deprecation warning, these test files will emit DeprecationWarning on every FeaturePlannedPayload instantiation:

File	Approximate instantiations
test_pipeline_payloads.py	~5 (TestFeaturePlannedPayload class)
test_event_type_schemas.py	~6 (via _make_feature_planned factory)
test_event_payloads_nc03.py	~3
The project doesn't configure filterwarnings in pyproject.toml, so these won't cause test failures today. But they'll produce noisy output, and if -W error is ever added, they'll break.

Recommendation: TASK-NCFA-001 scope should explicitly include wrapping existing FeaturePlannedPayload test instantiations with pytest.warns(DeprecationWarning) or adding a filterwarnings marker to those test classes.

Section 4: Regression Risk Assessment — Score: 7/10
Finding 10 (HIGH): Scope gap — EventType enum and _EVENT_TYPE_REGISTRY updates missing from task
TASK-NCFA-001's out-of-scope section states: "Any MessageEnvelope or NATSClient changes — only adding new payload classes and topic constants."

However, the new payloads require additions to:

EventType enum in envelope.py:42-76 — five new members
_EVENT_TYPE_REGISTRY in envelope.py:80-104 — five new entries
Without these, the payloads can't be dispatched via payload_class_for_event_type(), which breaks the entire envelope → payload routing pipeline.

Recommendation: Add an explicit scope item to TASK-NCFA-001:

"### 5. Update EventType and payload registry — Add BUILD_QUEUED, BUILD_PAUSED, BUILD_RESUMED, STAGE_COMPLETE, STAGE_GATED to EventType enum and _EVENT_TYPE_REGISTRY in envelope.py"

And update the out-of-scope note to: "Any MessageEnvelope schema changes or NATSClient changes" (distinguishing schema changes from registry additions).

Finding 11 (PASS): No circular import risk
Import chain is one-directional: __init__ → events/__init__ → events/_pipeline. Adding exports is safe.

Finding 12 (MEDIUM): Test noise from deprecation (see Finding 9)
Existing tests that instantiate FeaturePlannedPayload will emit warnings. Not a failure risk, but should be addressed in scope.

Finding 13 (PASS): Test discovery will work
testpaths = ["tests"] discovers recursively. The new tests/integration/ directory will work with @pytest.mark.integration exclusion.

Section 5: Integration Test Feasibility — Score: 8/10
Finding 14 (MEDIUM): Existing "integration" tests use mocks, not live NATS
The existing test_client_integration.py uses AsyncMock to simulate nats-py — it doesn't connect to a live server. TASK-NCFA-002 proposes actual live NATS tests against GB10.

The task says "Use the existing integration test fixtures (nats_client, jetstream_context)" but these fixtures don't exist in the current conftest. The task will need to create new fixtures for live NATS connectivity.

Recommendation: Update TASK-NCFA-002 to note that live NATS fixtures need to be created from scratch (a conftest.py in tests/integration/ with nats_client and jetstream_context fixtures). This adds scope but is necessary.

Finding 15 (PASS): AckWait redelivery test is feasible
The test requires a ~6s wait (5s AckWait + 1s buffer). This is reasonable for integration tests and JetStream pull consumers support this pattern.

Finding 16 (PASS): Wildcard subscription test is correctly scoped
pipeline.build-*.> will catch build events but not stage events. The test description correctly says "all build events" — this is accurate.

Section 6: Alignment with Anchor v2.2 — Score: 9/10
Finding 17 (PASS): Scope coverage appears complete
Five payloads, six topics, one deprecation — matches the README's description of corrections 26-30. (Cannot verify against the alignment review itself as it's in the forge repo.)

Finding 18 (PASS): Out-of-scope items are correctly deferred
FeatureReadyForBuildPayload — already exists in code, correctly left alone pending TASK-FVD3
Singular topic convention — already correctly implemented, no action needed
Recommendations Summary
#	Priority	Finding	Recommendation
1	MUST	EventType/registry gap (F10)	Add EventType enum + _EVENT_TYPE_REGISTRY updates to TASK-NCFA-001 scope
2	MUST	Deprecation mechanism (F8)	Specify model_post_init not __init_subclass__ or module-level
3	MUST	extra='allow' inconsistency (F2)	Decide and document whether all 5 or only BuildQueued uses extra='allow'
4	SHOULD	Test noise from deprecation (F9)	Add pytest.warns wrappers to existing tests in TASK-NCFA-001 scope
5	SHOULD	Live NATS fixtures don't exist (F14)	Update TASK-NCFA-002 to include fixture creation
6	COULD	correlation_id documentation (F1)	Add code comment explaining dual-level correlation
7	COULD	ALL_STAGES wildcard (F6)	Add convenience constant for stage event subscriptions

=========================================================================
DECISION CHECKPOINT
=========================================================================

Review Results:
  Architecture Score: 78/100
  Findings: 9 (3 HIGH, 3 MEDIUM, 3 LOW/PASS)
  Recommendations: 7 (3 MUST, 2 SHOULD, 2 COULD)

Verdict: PROCEED WITH MODIFICATIONS

The tasks are architecturally sound and represent the correct
approach for Forge v2.2 alignment. Three modifications are required
before implementation begins:

  1. Add EventType enum + registry updates to TASK-NCFA-001 scope
  2. Fix deprecation mechanism (use model_post_init)
  3. Decide on extra='allow' strategy for all five payloads

Decision Options:
  [A]ccept  — Approve findings, archive review
  [R]evise  — Request deeper analysis on specific areas
  [I]mplement — Apply modifications to task files, then proceed
  [C]ancel  — Discard review

=========================================================================
Your choice?

I

All modifications applied. Here's a summary of what was changed:


=========================================================================
REVIEW COMPLETE: TASK-7448 — Modifications Applied
=========================================================================

Files modified:
  TASK-NCFA-001-add-pipeline-payloads.md
    + Added EventType enum + registry updates as explicit scope item
    + Fixed deprecation mechanism → model_post_init
    + All 5 payloads now use ConfigDict(extra="allow")
    + Added existing test update scope for pytest.warns
    + Clarified out-of-scope re: envelope registry vs schema

  TASK-NCFA-002-integration-tests-new-payloads.md
    + Noted live NATS fixtures must be created from scratch
    + Clarified existing "integration" tests use AsyncMock

  IMPLEMENTATION-GUIDE.md
    + Added forward-compat decision note
    + Updated sketches: model_config, Field(description=...), float | None
    + Fixed deprecation mechanism to model_post_init

  TASK-7448-review-forge-v2-alignment-tasks.md
    + Status: backlog → review_complete
    + Added full review findings and test execution log

=========================================================================
Next steps:
  1. /task-work TASK-NCFA-001  (Wave 1 — payloads, topics, deprecation)
  2. /task-work TASK-NCFA-002  (Wave 2 — integration tests, depends on 001)
=========================================================================















GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-BEA5 --verbose --max-turns 30
