# nats-core — System Specification

## For: `/feature-spec` session · guardkit/nats-core repo · April 2026

---

## What is nats-core?

The shared contract layer for the entire Jarvis Ship's Computer fleet. A pip-installable
Python library containing:

1. **Message envelope schema** — Pydantic models defining the wire format for all NATS messages
2. **Event type schemas** — Typed payloads for every event in the system (pipeline, agent, approval, Jarvis)
3. **Topic registry** — Typed constants for all NATS subjects (no magic strings anywhere)
4. **Connection helpers** — Thin wrapper around nats-py providing typed publish/subscribe
5. **Multi-tenancy support** — Project-scoped topic resolution with account isolation

Every agent, adapter, and service in the fleet depends on this library. Schema changes
require semver coordination. This is the lowest-velocity, highest-impact package in the
ecosystem.

**Template:** Built from `python-library` template (once created).

---

## Relationship to Existing Architecture

This library implements the schemas and topic structures designed in:

- **Ship's Computer Architecture** (v1.0, Jan 2026) — `agents.*` topic namespace, base message envelope
- **Dev Pipeline Architecture** (v1.0, Feb 2026) — `pipeline.*` topic namespace, build event schemas
- **Dev Pipeline System Spec** (v1.0, Feb 2026) — COMP-nats-core component definition, XC-schema-versioning
- **Jarvis Vision** (Mar 2026) — `jarvis.*` topic namespace, intent classification dispatch

All topic structures and message schemas referenced below are drawn from these documents.
This spec consolidates and refines them into implementable features.

---

## Resolved Decisions (from existing architecture — Do NOT reopen)

| # | Decision | Resolution | Source |
|---|----------|-----------|--------|
| ADR-SP-001 | Message bus | NATS with JetStream | Dev Pipeline System Spec |
| ADR-SP-002 | State ownership | NATS event bus owns workflow state transitions | Dev Pipeline System Spec |
| XC-schema-versioning | Schema evolution | `version` field in envelope, Pydantic `extra="ignore"`, semver on package | Dev Pipeline System Spec |
| D4 | Event bus | NATS JetStream (fleet-wide) | Fleet Master Index |

---

## Package Structure

```
nats-core/
├── src/
│   └── nats_core/
│       ├── __init__.py          # Public API re-exports
│       ├── py.typed             # PEP 561 marker
│       ├── envelope.py          # MessageEnvelope base schema
│       ├── events/
│       │   ├── __init__.py
│       │   ├── pipeline.py      # FeaturePlanned, BuildStarted, BuildProgress, etc.
│       │   ├── agent.py         # StatusUpdate, ApprovalRequest, ApprovalResponse, etc.
│       │   └── jarvis.py        # IntentClassified, DispatchCommand, AgentResult
│       ├── topics.py            # Topic registry with typed constants
│       ├── client.py            # NATSClient — typed publish/subscribe wrapper
│       └── config.py            # pydantic-settings for NATS connection config
├── tests/
│   ├── test_envelope.py
│   ├── test_events.py
│   ├── test_topics.py
│   ├── test_client.py           # Unit tests (mocked nats-py)
│   └── test_integration.py      # Integration tests (real NATS, -m integration)
├── pyproject.toml
└── README.md
```

---

## Feature 1: Message Envelope

The base message format for all NATS communication in the fleet.

### Schema

```python
class MessageEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Tolerate unknown fields (forward compat)

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str = "1.0"
    source_id: str                    # e.g., "jarvis-router", "guardkit-factory", "telegram-adapter"
    event_type: EventType
    project: str | None = None        # e.g., "finproxy", "guardkit" — None for fleet-wide
    correlation_id: str | None = None # Links related messages (e.g., ideation → PO → architect chain)
    payload: dict[str, Any]
```

### Acceptance Criteria (BDD)

```gherkin
Feature: Message Envelope Serialisation

  Scenario: Create envelope with defaults
    Given no explicit message_id or timestamp
    When I create a MessageEnvelope with source_id "test" and event_type STATUS
    Then message_id should be a valid UUID v4
    And timestamp should be within 1 second of now (UTC)
    And version should be "1.0"

  Scenario: Serialise envelope to JSON
    Given a MessageEnvelope with known fields
    When I call model_dump_json()
    Then the output should be valid JSON
    And timestamp should be ISO 8601 format
    And all fields should be present

  Scenario: Deserialise envelope from JSON with unknown fields
    Given a JSON string with an extra field "future_field"
    When I parse it as MessageEnvelope
    Then it should parse without error
    And the unknown field should be silently ignored

  Scenario: Deserialise envelope with missing required field
    Given a JSON string without source_id
    When I parse it as MessageEnvelope
    Then it should raise a ValidationError

  Scenario: Correlation ID links related messages
    Given an envelope with correlation_id "session-abc-123"
    When I create a response envelope with the same correlation_id
    Then both envelopes share the same correlation_id
    And they have different message_ids
```

---

## Feature 2: Event Type Schemas

Typed payload schemas for every event in the system.

### Pipeline Events

```python
class EventType(str, Enum):
    # Pipeline events
    FEATURE_PLANNED = "feature_planned"
    READY_FOR_DEV = "ready_for_dev"
    BUILD_STARTED = "build_started"
    BUILD_PROGRESS = "build_progress"
    BUILD_COMPLETE = "build_complete"
    BUILD_FAILED = "build_failed"
    TICKET_UPDATED = "ticket_updated"

    # Agent events (Ship's Computer)
    STATUS = "status"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    COMMAND = "command"
    RESULT = "result"
    ERROR = "error"

    # Jarvis events
    INTENT_CLASSIFIED = "intent_classified"
    DISPATCH = "dispatch"
    AGENT_RESULT = "agent_result"
    NOTIFICATION = "notification"
```

### Key Payload Schemas

```python
# Pipeline
class FeaturePlannedPayload(BaseModel):
    feature_id: str
    feature_name: str
    repo: str
    branch: str | None = None
    wave_count: int
    task_count: int
    waves: list[WaveSummary]
    feature_yaml_path: str
    ticket_id: str | None = None

class BuildProgressPayload(BaseModel):
    feature_id: str
    build_id: str          # format: build-{feature_id}-{YYYYMMDDHHMMSS}
    wave: int
    wave_total: int
    tasks: list[TaskProgress]
    overall_progress_pct: float  # 0.0 - 100.0
    elapsed_seconds: int
    current_task: str | None = None

class BuildCompletePayload(BaseModel):
    feature_id: str
    build_id: str
    repo: str
    branch: str
    pr_url: str | None = None
    duration_seconds: int
    tasks_completed: int
    tasks_failed: int
    tasks_total: int
    summary: str

class BuildFailedPayload(BaseModel):
    feature_id: str
    build_id: str
    failure_reason: str
    failed_task: str | None = None
    recoverable: bool = False

# Agent status
class AgentStatusPayload(BaseModel):
    state: Literal["running", "idle", "awaiting_approval", "error", "paused"]
    task_description: str | None = None
    progress: ProgressInfo | None = None
    metrics: dict[str, Any] | None = None

# Approval
class ApprovalRequestPayload(BaseModel):
    request_id: str
    agent_id: str
    action_description: str
    risk_level: Literal["low", "medium", "high"]
    details: dict[str, Any]
    timeout_seconds: int = 300

class ApprovalResponsePayload(BaseModel):
    request_id: str
    decision: Literal["approve", "reject", "defer", "override"]
    responder: str
    reason: str | None = None

# Jarvis
class IntentClassifiedPayload(BaseModel):
    original_text: str
    intent: str           # e.g., "software.build", "ideate", "general"
    confidence: float
    target_agent: str
    adapter_source: str   # e.g., "telegram", "reachy-bridge", "cli"

class DispatchPayload(BaseModel):
    target_agent: str
    original_text: str
    intent: str
    context: dict[str, Any] | None = None  # Session context for multi-turn
    correlation_id: str
```

### Acceptance Criteria (BDD)

```gherkin
Feature: Event Type Schemas

  Scenario: Build ID follows naming convention
    Given a feature_id "FEAT-AC1A"
    When I create a BuildStartedPayload
    Then build_id should match pattern "build-FEAT-AC1A-{YYYYMMDDHHMMSS}"

  Scenario: Build progress percentage bounds
    When I create a BuildProgressPayload with overall_progress_pct 150.0
    Then it should raise a ValidationError
    And the error should indicate the value must be between 0.0 and 100.0

  Scenario: Approval request has reasonable timeout default
    When I create an ApprovalRequestPayload without specifying timeout
    Then timeout_seconds should be 300

  Scenario: Intent classification includes confidence score
    Given an IntentClassifiedPayload with intent "ideate" and confidence 0.87
    When I serialise and deserialise it
    Then the confidence should be 0.87
    And the intent should be "ideate"

  Scenario: All event types have a corresponding payload class
    Given the EventType enum
    When I check each event type
    Then there should be a Pydantic payload class for every EventType value

  Scenario: Payload schemas use strict types not dict[str, Any]
    Given any payload class (except generic error)
    When I inspect its fields
    Then no field should be untyped dict[str, Any] at the top level
    # (nested dict is acceptable for extensible metadata only)
```

---

## Feature 3: Topic Registry

Typed constants eliminating magic strings across the fleet.

### Schema

```python
class Topics:
    class Pipeline:
        FEATURE_PLANNED = "pipeline.feature-planned.{feature_id}"
        READY_FOR_DEV = "pipeline.ready-for-dev.{feature_id}"
        BUILD_STARTED = "pipeline.build-started.{feature_id}"
        BUILD_PROGRESS = "pipeline.build-progress.{feature_id}"
        BUILD_COMPLETE = "pipeline.build-complete.{feature_id}"
        BUILD_FAILED = "pipeline.build-failed.{feature_id}"
        TICKET_UPDATED = "pipeline.ticket-updated.{feature_id}"
        ALL = "pipeline.>"
        ALL_BUILDS = "pipeline.build-*.>"

    class Agents:
        STATUS = "agents.status.{agent_id}"
        STATUS_ALL = "agents.status.>"
        APPROVAL_REQUEST = "agents.approval.{agent_id}.{task_id}"
        APPROVAL_RESPONSE = "agents.approval.{agent_id}.{task_id}.response"
        COMMAND = "agents.command.{agent_id}"
        RESULT = "agents.result.{agent_id}"

    class Jarvis:
        COMMAND = "jarvis.command.{adapter}"
        INTENT_CLASSIFIED = "jarvis.intent.classified"
        DISPATCH = "jarvis.dispatch.{agent}"
        NOTIFICATION = "notifications.{adapter}"

    class System:
        HEALTH = "system.health.{component}"

    @staticmethod
    def for_project(project: str, topic: str) -> str:
        """Scope a topic to a project namespace for multi-tenancy.

        Example: Topics.for_project("finproxy", "pipeline.build-started.FEAT-001")
                 → "finproxy.pipeline.build-started.FEAT-001"
        """
        return f"{project}.{topic}"

    @staticmethod
    def resolve(template: str, **kwargs) -> str:
        """Resolve a topic template with concrete values.

        Example: Topics.resolve(Topics.Pipeline.BUILD_STARTED, feature_id="FEAT-001")
                 → "pipeline.build-started.FEAT-001"
        """
        return template.format(**kwargs)
```

### Acceptance Criteria (BDD)

```gherkin
Feature: Topic Registry

  Scenario: Resolve a pipeline topic with feature_id
    When I resolve Topics.Pipeline.BUILD_STARTED with feature_id "FEAT-AC1A"
    Then the result should be "pipeline.build-started.FEAT-AC1A"

  Scenario: Scope a topic to a project
    Given a resolved topic "pipeline.build-started.FEAT-001"
    When I scope it to project "finproxy"
    Then the result should be "finproxy.pipeline.build-started.FEAT-001"

  Scenario: Wildcard topics are valid NATS subjects
    When I access Topics.Pipeline.ALL
    Then the value should be "pipeline.>"
    And it should be a valid NATS wildcard subject

  Scenario: All topic templates have matching event types
    Given the Topics registry
    When I collect all topic templates
    Then every topic in Pipeline should correspond to an EventType
    And every topic in Agents should correspond to an EventType

  Scenario: No magic strings in consuming code
    Given a service that publishes BUILD_COMPLETE events
    When I search the codebase for hardcoded topic strings
    Then no file outside topics.py should contain "pipeline.build-"
```

---

## Feature 4: NATS Client

Thin typed wrapper providing convenience methods for publish/subscribe.

### Design Principles

- Wraps nats-py (not FastStream — that's for services, this is the shared library)
- Typed convenience methods per event type
- Automatic envelope wrapping/unwrapping
- Connection config via pydantic-settings
- Unit tests mock nats-py; integration tests use real NATS

### Acceptance Criteria (BDD)

```gherkin
Feature: NATS Client

  Scenario: Publish a typed event
    Given a connected NATSClient
    When I call publish_build_complete with a BuildCompletePayload
    Then the client should publish to the correct topic
    And the message should be a JSON-serialised MessageEnvelope
    And the envelope source_id should identify the publisher
    And the payload should contain the BuildCompletePayload fields

  Scenario: Subscribe with typed handler
    Given a connected NATSClient
    When I subscribe to Topics.Pipeline.BUILD_COMPLETE with a typed handler
    And a BUILD_COMPLETE message arrives
    Then the handler should receive a deserialised MessageEnvelope
    And envelope.payload should be parseable as BuildCompletePayload

  Scenario: Connection from environment config
    Given NATS_URL environment variable set to "nats://100.x.y.z:4222"
    When I create a NATSClient with default config
    Then it should connect to "nats://100.x.y.z:4222"

  Scenario: Connection with retry on failure
    Given NATS server is temporarily unavailable
    When the client attempts to connect
    Then it should retry with exponential backoff
    And it should not crash on transient failures

  Scenario: Graceful disconnect
    Given a connected NATSClient with active subscriptions
    When I call disconnect()
    Then all subscriptions should be drained
    And the connection should close cleanly

  Scenario: Project-scoped publish
    Given a connected NATSClient
    When I call publish_build_complete with project="finproxy"
    Then the topic should be prefixed with "finproxy."
    And the envelope project field should be "finproxy"
```

---

## Feature 5: Configuration

Connection and behaviour settings via pydantic-settings.

```python
class NATSConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NATS_")

    url: str = "nats://localhost:4222"
    connect_timeout: float = 5.0
    reconnect_time_wait: float = 2.0
    max_reconnect_attempts: int = 60
    name: str = "nats-core-client"     # Client name visible in NATS monitoring
    user: str | None = None            # For account-based auth
    password: str | None = None
    creds_file: str | None = None      # NKey credentials file path
```

### Acceptance Criteria (BDD)

```gherkin
Feature: NATS Configuration

  Scenario: Default configuration connects to localhost
    Given no environment variables set
    When I create a NATSConfig
    Then url should be "nats://localhost:4222"

  Scenario: Environment variable override
    Given NATS_URL is set to "nats://gb10.tail:4222"
    When I create a NATSConfig
    Then url should be "nats://gb10.tail:4222"

  Scenario: Credentials file for account auth
    Given NATS_CREDS_FILE is set to "/etc/nats/appmilla.creds"
    When I create a NATSConfig
    Then creds_file should point to the credentials file
```

---

## Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| Zero runtime dependencies beyond nats-py + pydantic | Minimal footprint | Every agent installs this |
| 100% type coverage (py.typed, mypy strict) | Library consumers get type checking | PEP 561 compliance |
| All unit tests run without NATS server | Fast CI, no infrastructure deps | TestNatsBroker or mocked nats-py |
| Semver versioned | Coordinated schema evolution | Breaking changes = major bump |
| Python 3.12+ | Match fleet minimum | All agents target 3.12+ |

---

## Dependencies

```toml
[project]
dependencies = [
    "nats-py>=2.7.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.3",
    "mypy>=1.8",
]
```

---

## Build Approach

```bash
# 1. Create python-library template (if not yet done)
cd ~/Projects/appmilla_github/guardkit
/template-create --name python-library --path ~/Projects/appmilla_github/youtube-transcript-mcp

# 2. Bootstrap nats-core from template
cd ~/Projects/appmilla_github/nats-core
guardkit init python-library

# 3. Run /feature-spec for each feature above
/feature-spec "Message Envelope" --context docs/design/specs/nats-core-system-spec.md

# 4. Run /feature-plan for implementation tasks
/feature-plan

# 5. AutoBuild
autobuild
```
