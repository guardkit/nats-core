# API Contract: Message Contracts

**Bounded Context:** Message Contracts (envelope.py, events/)
**Protocols:** NATS Events, Python Public API
**Version:** 1.0.0
**Date:** 2026-04-07

---

## Python Public API

### Re-exports from `nats_core`

```python
# Envelope and discriminator
from nats_core.envelope import MessageEnvelope, EventType

# Dispatch helper
from nats_core.envelope import payload_class_for_event_type

# Pipeline events
from nats_core.events.pipeline import (
    FeaturePlannedPayload,
    FeatureReadyForBuildPayload,
    BuildStartedPayload,
    BuildProgressPayload,
    BuildCompletePayload,
    BuildFailedPayload,
)

# Agent events
from nats_core.events.agent import (
    AgentStatusPayload,
    ApprovalRequestPayload,
    ApprovalResponsePayload,
)

# Jarvis events
from nats_core.events.jarvis import (
    IntentClassifiedPayload,
    DispatchPayload,
)

# Fleet events
from nats_core.events.fleet import (
    AgentHeartbeatPayload,
    AgentDeregistrationPayload,
)
```

### Helper: payload_class_for_event_type

```python
def payload_class_for_event_type(event_type: EventType) -> type[BaseModel]:
    """Return the Pydantic payload class for a given EventType.

    Raises:
        KeyError: If no payload class is registered for the event type.
    """
```

---

## NATS Event Contracts

### Pipeline Domain

| Event Type | Topic Pattern | Payload Model | Publisher |
|------------|---------------|---------------|-----------|
| `feature_planned` | `pipeline.feature-planned.{feature_id}` | `FeaturePlannedPayload` | Pipeline Orchestrator |
| `feature_ready_for_build` | `pipeline.feature-ready-for-build.{feature_id}` | `FeatureReadyForBuildPayload` | Pipeline Orchestrator |
| `build_started` | `pipeline.build-started.{feature_id}` | `BuildStartedPayload` | GuardKit Factory |
| `build_progress` | `pipeline.build-progress.{feature_id}` | `BuildProgressPayload` | GuardKit Factory |
| `build_complete` | `pipeline.build-complete.{feature_id}` | `BuildCompletePayload` | GuardKit Factory |
| `build_failed` | `pipeline.build-failed.{feature_id}` | `BuildFailedPayload` | GuardKit Factory |

### Agent Domain

| Event Type | Topic Pattern | Payload Model | Publisher |
|------------|---------------|---------------|-----------|
| `status` | `agents.status.{agent_id}` | `AgentStatusPayload` | Any agent |
| `approval_request` | `agents.approval.{agent_id}.{task_id}` | `ApprovalRequestPayload` | Any agent |
| `approval_response` | `agents.approval.{agent_id}.{task_id}.response` | `ApprovalResponsePayload` | Human / Jarvis |
| `command` | `agents.command.{agent_id}` | (generic) | Jarvis / adapters |
| `result` | `agents.result.{agent_id}` | (generic) | Any agent |
| `error` | `agents.status.{agent_id}` | `AgentStatusPayload` (state=error) | Any agent |

### Jarvis Domain

| Event Type | Topic Pattern | Payload Model | Publisher |
|------------|---------------|---------------|-----------|
| `intent_classified` | `jarvis.intent.classified` | `IntentClassifiedPayload` | Jarvis Router |
| `dispatch` | `jarvis.dispatch.{agent}` | `DispatchPayload` | Jarvis Router |
| `agent_result` | `jarvis.dispatch.{agent}` | (generic result) | Target agent |
| `notification` | `jarvis.notification.{adapter}` | (notification data) | Jarvis Router |

### Fleet Domain

| Event Type | Topic Pattern | Payload Model | Publisher |
|------------|---------------|---------------|-----------|
| `agent_register` | `fleet.register` | `AgentManifest` (full manifest) | Any agent |
| `agent_heartbeat` | `fleet.heartbeat.{agent_id}` | `AgentHeartbeatPayload` | Any agent |
| `agent_deregister` | `fleet.deregister` | `AgentDeregistrationPayload` | Any agent |

---

## Wire Format

All messages use `MessageEnvelope` as the wire format:

```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-04-07T14:30:00Z",
  "version": "1.0",
  "source_id": "guardkit-factory",
  "event_type": "build_complete",
  "project": "finproxy",
  "correlation_id": "session-abc-123",
  "payload": {
    "feature_id": "FEAT-001",
    "build_id": "build-FEAT-001-20260407143000",
    "repo": "finproxy",
    "branch": "feature/FEAT-001",
    "pr_url": "https://github.com/appmilla/finproxy/pull/42",
    "duration_seconds": 120,
    "tasks_completed": 5,
    "tasks_failed": 0,
    "tasks_total": 5,
    "summary": "All 5 tasks completed successfully"
  }
}
```

---

## Schema Versioning (ADR-002)

- `MessageEnvelope.version` = "1.0" (current)
- `ConfigDict(extra="ignore")` on all models -- tolerate unknown fields
- New fields MUST be optional with defaults
- Breaking changes require major version bump (from v1.0 onwards)

---

## Design Decisions

- DDR-001: Replace READY_FOR_DEV with FEATURE_READY_FOR_BUILD
- DDR-002: Publish full AgentManifest for fleet registration
