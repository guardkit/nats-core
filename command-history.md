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