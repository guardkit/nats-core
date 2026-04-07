/system-arch \
  --from docs/design/specs/nats-core-system-spec.md \
  --context docs/design/decisions/ADR-001-nats-as-event-bus.md \
  --context docs/design/decisions/ADR-004-dynamic-fleet-registration.md

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SYSTEM ARCHITECTURE: nats-core
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mode: setup (no existing architecture context found)

Graphiti: available (project: nats-core, FalkorDB on whitestocks)

Context loaded:

nats-core-system-spec.md — system spec (source document)
ADR-001-nats-as-event-bus.md — NATS as event bus
ADR-004-dynamic-fleet-registration.md — CAN bus fleet registration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category 1: Domain & Structural Pattern
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From the system spec, I can see this is a shared contract library — the schema and topic layer for a NATS-based agent fleet ("Jarvis Ship's Computer"). Let me confirm the details with you.

Q1. What does this system do?

From the spec: "The shared contract layer for the entire Jarvis Ship's Computer fleet — a pip-installable Python library containing message envelope schemas, event type schemas, topic registry, connection helpers, and multi-tenancy support."

Q2. Who are the primary users?

From the spec: Agent developers, service authors, and adapter builders across the fleet — every agent, adapter, and service depends on this library.

Q3. What are the core business domains?

From the spec I see these domain areas:

Messaging — envelope schema, serialisation
Pipeline Events — build lifecycle (planned → started → progress → complete/failed)
Agent Events — status, approval, commands, results
Jarvis Events — intent classification, dispatch, notifications
Fleet Registration — agent discovery, heartbeat, routing
Configuration — connection settings, multi-tenancy
Q4. Structural pattern:

AskUserQuestion
OUT
User has answered your questions: "Do the pre-filled answers for Q1-Q3 above look correct, or do you want to revise any of them?"="Looks correct", "What structural pattern best fits nats-core? Given this is a shared library (not a service), the pattern governs how the library's internal modules are organised."="Modular Monolith (Recommended)". You can now continue with the user's answers in mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category 1: Domain & Structural Pattern
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Captured:

Purpose: Shared contract layer for the Jarvis Ship's Computer fleet — schemas, topics, typed client
Users: Agent developers, service authors, adapter builders
Domains: Messaging, Pipeline Events, Agent Events, Jarvis Events, Fleet Registration, Configuration
Structural Pattern: Modular Monolith — single cohesive package with well-defined internal modules
ADR to capture:

ADR-ARCH-001: Modular Monolith pattern for shared library organisation
AskUserQuestion
OUT
User has answered your questions: "Category 1 checkpoint — how would you like to proceed?"="Continue". You can now continue with the user's answers in mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category 2: Bounded Contexts / Module Structure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From the system spec, the package structure is already well-defined. Let me confirm the module breakdown:

Q5. Major modules/components:

From the spec:

Module	File(s)	Description
Envelope	envelope.py	Base MessageEnvelope schema — wire format for all NATS messages
Events	events/ (pipeline, agent, jarvis, fleet)	Typed payload schemas per event domain
Manifest	manifest.py	AgentManifest, ToolCapability, IntentCapability
Topics	topics.py	Topic registry with typed constants, resolution, project scoping
Client	client.py	Typed publish/subscribe wrapper around nats-py
Config	config.py	NATSConfig via pydantic-settings
Q6. Module responsibilities and ownership:

Envelope owns the wire format — all messages go through MessageEnvelope
Events owns typed payloads — each sub-module owns its event domain
Manifest owns agent capability descriptions (used by fleet registration)
Topics owns subject string constants — single source of truth, no magic strings
Client owns connection lifecycle and typed pub/sub convenience methods
Config owns connection settings via environment variables
Q7. What data does each module own?

Envelope → MessageEnvelope model (message_id, timestamp, version, source_id, event_type, payload)
Events → EventType enum + all payload models (pipeline, agent, jarvis, fleet)
Manifest → AgentManifest, IntentCapability, ToolCapability
Topics → Topics class with nested namespaces (Pipeline, Agents, Fleet, Jarvis, System)
Client → NATSClient (stateful — holds connection, subscriptions)
Config → NATSConfig (pydantic-settings model)
AskUserQuestion
OUT
User has answered your questions: "Does this module structure match your intent? The spec shows a clear layered dependency: Config → Client → Topics → Events → Envelope. Anything to add or change?"="Correct as captured", "Category 2 checkpoint — how would you like to proceed?"="Continue". You can now continue with the user's answers in mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category 2: Module Structure — Captured
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

6 modules with clear dependency chain:
Config → Client → Topics → Events → Envelope

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category 3: Technology & Infrastructure
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From the spec and CLAUDE.md, I can pre-fill most of this:

Q8. Languages & frameworks:

Python >=3.10 (spec says 3.12+, CLAUDE.md says >=3.10)
Pydantic v2 for schemas
pydantic-settings v2 for config
nats-py >=2.7.0 for NATS client
Q9. Databases & data stores:

NATS JetStream (message persistence)
NATS KV (agent-registry bucket for fleet routing table)
No traditional database — this is a library, not a service
Q10. Deployment model:

pip-installable library (not deployed as a service)
Consumed as a dependency by all fleet agents/services
Built with hatchling, distributed via PyPI or private index
Q11. CI/CD pipeline:

pytest (asyncio_mode="auto") for testing
ruff for linting
mypy strict for type checking
hatchling for build
Q12. External services/integrations:

nats-py (sole runtime dependency beyond pydantic)
NATS server (runtime — consumed by dependents, not this library directly)
AskUserQuestion
OUT
User has answered your questions: "The spec says Python 3.12+ but CLAUDE.md says >=3.10. Which minimum Python version should the architecture target?"="Python >=3.12", "What CI/CD platform will run the test/lint/build pipeline?"="GitHub Actions", "Category 3 checkpoint — how would you like to proceed?"="Continue". You can now continue with the user's answers in mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category 3: Technology & Infrastructure — Captured
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Language: Python >=3.12
Frameworks: Pydantic v2, pydantic-settings v2, nats-py >=2.7.0
Data stores: NATS JetStream + KV (no traditional DB)
Deployment: pip-installable library (hatchling build)
CI/CD: GitHub Actions (pytest, ruff, mypy strict)
External: NATS server (runtime dependency of consumers)
ADRs to capture:

ADR-ARCH-002: Python 3.12+ minimum version (match fleet target)
ADR-ARCH-003: Zero runtime deps beyond nats-py + pydantic
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category 4: Multi-Consumer API Strategy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Since nats-core is a library (not a service), its "consumers" are Python packages that import it. The API surface is the public Python API.

Q13. Consumer types:

Consumer	How they use nats-core
Agent services (Jarvis, PO Agent, Architect, etc.)	Import models, publish/subscribe via NATSClient
Adapters (Telegram, Reachy Bridge, CLI)	Import Jarvis event schemas, publish commands
Pipeline orchestrators (GuardKit Factory)	Import pipeline event schemas, publish build events
Test suites (across the fleet)	Import models for test assertions, mock data factories
Q14. API protocols:

Python import API (the only protocol — this is a library)
Public API surface defined in __init__.py re-exports
Q15. Different data shapes per consumer?

No — all consumers share the same Pydantic models
Each consumer uses a subset (pipeline agents use pipeline events, Jarvis uses jarvis events, etc.)
Q16. Auth per consumer type?

N/A at library level — auth is handled by NATSConfig (creds_file, user/password) passed at connection time by each consuming service
AskUserQuestion
OUT
User has answered your questions: "The API surface for nats-core is purely a Python import API since it's a library. Does the summary above capture the consumer landscape correctly?"="Correct", "Category 4 checkpoint — how would you like to proceed?"="Continue". You can now continue with the user's answers in mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category 5: Cross-Cutting Concerns
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q17. Authentication/Authorization:

Delegated to NATS server — NATSConfig provides credentials (user/password, creds file, NKey)
Library provides config model, not auth logic itself
NATS account isolation handles multi-tenancy (per ADR-001)
Q18. Logging/Observability:

stderr-only logging (per CLAUDE.md — never print())
Structured logging in the NATSClient for connection lifecycle events
No tracing/metrics at library level (consumers add their own)
Q19. Error Handling:

Pydantic ValidationError for schema violations (raised naturally)
Connection errors from nats-py bubbled up with retry/backoff in NATSClient
No custom exception hierarchy needed (library is thin)
Q20. Data Validation:

Pydantic models at all boundaries — MessageEnvelope validates on deserialise
extra="ignore" for forward compatibility (unknown fields silently dropped)
Field constraints (ge, le, min_length) on payload models
field_validator for complex rules (e.g., build_id format)
Q21. Other cross-cutting concerns:

Schema versioning — version field in envelope, semver on package (per XC-schema-versioning)
Forward compatibility — extra="ignore" on all models so older consumers tolerate new fields
Correlation tracking — correlation_id in envelope links related messages across the fleet
AskUserQuestion
OUT
User has answered your questions: "Do these cross-cutting concerns capture the right approach? Particularly: (1) stderr-only logging, (2) no custom exception hierarchy, (3) schema versioning via envelope version field + semver."="Correct as captured", "Category 5 checkpoint — how would you like to proceed?"="Continue". You can now continue with the user's answers in mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Category 6: Constraints & NFRs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From the system spec's Non-Functional Requirements table:

Q22. Performance:

Not directly applicable — this is a library, not a service
NATS pub/sub is sub-millisecond (per ADR-001), but that's the server, not this library
Library should add negligible overhead (Pydantic serialisation is fast)
Q23. Scalability:

N/A for the library itself — scalability is handled by NATS server and consuming services
Library supports multi-tenancy via Topics.for_project() for project scoping
Q24. Compliance/Regulatory:

No direct compliance requirements on the library
FinProxy scoping via NATS accounts is an architectural concern of the fleet, not this package
Q25. Availability/SLA:

N/A — library availability = "can it be pip installed"
Connection retry with exponential backoff in NATSClient supports consumer availability
Q26. Security:

No secrets stored in the library
NATSConfig accepts credentials via environment variables (never hardcoded)
Creds file path support for NKey-based auth
Q27. Quality constraints (from spec):

Constraint	Target
Zero runtime deps beyond nats-py + pydantic	Minimal install footprint
100% type coverage (py.typed, mypy strict)	PEP 561 compliance
All unit tests run without NATS server	Fast CI, no infra deps
Semver versioned	Coordinated schema evolution
Python 3.12+	Match fleet minimum
AskUserQuestion
OUT
User has answered your questions: "The NFRs are mostly quality constraints (type coverage, test isolation, semver, minimal deps) rather than performance/scalability targets, since this is a library. Anything to add?"="Correct as captured", "Category 6 checkpoint — all 6 categories complete. Ready to generate C4 diagrams?"="Generate diagrams". You can now continue with the user's answers in mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C4 CONTEXT DIAGRAM REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


C4Context
    title nats-core System Context

    Person(agent_dev, "Agent Developer", "Builds agents and services for the fleet")
    Person(adapter_dev, "Adapter Developer", "Builds Telegram, Reachy, CLI adapters")

    System(nats_core, "nats-core", "Shared contract library: message schemas, topic registry, typed NATS client")

    System_Ext(jarvis, "Jarvis Router", "Intent classification and agent dispatch")
    System_Ext(po_agent, "Product Owner Agent", "Feature ideation and planning")
    System_Ext(architect, "Architect Agent", "System design and ADRs")
    System_Ext(guardkit, "GuardKit Factory", "Automated build pipeline")
    System_Ext(telegram, "Telegram Adapter", "Chat interface to Jarvis")
    System_Ext(reachy, "Reachy Bridge", "Robot voice interface")
    System_Ext(nats_server, "NATS Server", "JetStream message broker + KV store")

    Rel(agent_dev, nats_core, "pip install, import")
    Rel(adapter_dev, nats_core, "pip install, import")
    Rel(jarvis, nats_core, "Imports schemas, uses NATSClient")
    Rel(po_agent, nats_core, "Imports event schemas")
    Rel(architect, nats_core, "Imports event schemas")
    Rel(guardkit, nats_core, "Imports pipeline events, publishes build status")
    Rel(telegram, nats_core, "Imports Jarvis events")
    Rel(reachy, nats_core, "Imports Jarvis events")
    Rel(nats_core, nats_server, "NATSClient connects via nats-py")
Look for: all fleet consumers depending on nats-core, single connection path to NATS server via the client module.

AskUserQuestion
OUT
User has answered your questions: "Does this C4 Context diagram accurately represent the system context? It shows nats-core as a library consumed by all fleet agents/adapters, with a single outbound dependency on NATS server."="Approve". You can now continue with the user's answers in mind.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
C4 CONTAINER DIAGRAM REVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


C4Container
    title Container Diagram for nats-core

    Container_Boundary(nats_core, "nats-core (Python library)") {
        Container(envelope, "envelope.py", "Pydantic", "MessageEnvelope base schema — wire format for all messages")
        Container(events, "events/", "Pydantic", "Typed payload schemas: pipeline, agent, jarvis, fleet")
        Container(manifest, "manifest.py", "Pydantic", "AgentManifest, IntentCapability, ToolCapability")
        Container(topics, "topics.py", "Python", "Topic registry — typed constants, resolution, project scoping")
        Container(client, "client.py", "nats-py", "NATSClient — typed publish/subscribe, fleet convenience methods")
        Container(config, "config.py", "pydantic-settings", "NATSConfig — connection settings from environment")
    }

    System_Ext(nats_server, "NATS Server", "JetStream broker + KV store")
    System_Ext(consumer, "Fleet Agents & Adapters", "All consuming services")

    Rel(consumer, envelope, "Import MessageEnvelope")
    Rel(consumer, events, "Import event payload models")
    Rel(consumer, manifest, "Import AgentManifest")
    Rel(consumer, topics, "Import topic constants")
    Rel(consumer, client, "Use NATSClient for pub/sub")

    Rel(client, config, "Reads connection settings")
    Rel(client, topics, "Resolves topic strings")
    Rel(client, envelope, "Wraps/unwraps messages")
    Rel(client, nats_server, "Connects via nats-py")
    Rel(events, envelope, "Payloads carried in envelope")
    Rel(manifest, events, "IntentCapability used in fleet events")
Look for: clear dependency flow from Client → Topics → Events → Envelope, Config feeds Client only, all consumer imports flow into the library boundary.

AskUserQuestion
OUT
User has answered your questions: "Does this C4 Container diagram accurately represent the internal modules and their relationships? It shows the dependency chain: Client → Topics → Events → Envelope, with Config feeding into Client."="Approve". You can now continue with the user's answers in mind.
Both diagrams approved. Now generating all architecture artefacts.

Graphiti seeding failed -- the Graphiti client requires an LLM API key that isn't configured in the current shell environment.


WARNING: Graphiti seeding failed.
Reason: LLM API key not configured (OPENAI_API_KEY or equivalent not set).
Markdown artefacts are still fully generated in docs/architecture/.
Re-seed when Graphiti LLM credentials are available.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE DOCUMENTATION CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


Created: docs/architecture/
  ├── ARCHITECTURE.md          (index + summary)
  ├── domain-model.md          (entities, relationships, topic structure)
  ├── system-context.md        (C4 Level 1)
  ├── container.md             (C4 Level 2)
  ├── assumptions.yaml         (10 assumptions)
  └── decisions/
      ├── ADR-ARCH-001-modular-monolith-pattern.md
      ├── ADR-ARCH-002-python-312-minimum.md
      └── ADR-ARCH-003-minimal-runtime-dependencies.md
Graphiti: NOT seeded (LLM API key missing). Artefacts available as markdown.

Next steps:

Review: ARCHITECTURE.md
Design APIs: /system-design with the system spec
Plan features: /system-plan for implementation planning

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
