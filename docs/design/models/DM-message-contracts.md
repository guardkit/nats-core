# Data Model: Message Contracts

**Design Unit:** Message Contracts (envelope.py, events/)
**Date:** 2026-04-07

---

## Entity: MessageEnvelope

The root wire format for all NATS messages in the fleet.

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `message_id` | `str` | UUID v4 auto | Valid UUID v4 | Unique message identifier |
| `timestamp` | `datetime` | UTC now auto | UTC timezone | Message creation time |
| `version` | `str` | `"1.0"` | | Schema version |
| `source_id` | `str` | (required) | Non-empty | Originating service/agent |
| `event_type` | `EventType` | (required) | Valid enum value | Payload discriminator |
| `project` | `str \| None` | `None` | | Multi-tenancy scope |
| `correlation_id` | `str \| None` | `None` | | Links related messages |
| `payload` | `dict[str, Any]` | (required) | | Event-specific data |

**Config:** `extra="ignore"` (forward compatibility per ADR-002)

---

## Entity: EventType (Enum)

Discriminator enum with values across four domains.

### Pipeline Domain

| Value | Constant | Payload Class |
|-------|----------|---------------|
| `"feature_planned"` | `FEATURE_PLANNED` | `FeaturePlannedPayload` |
| `"feature_ready_for_build"` | `FEATURE_READY_FOR_BUILD` | `FeatureReadyForBuildPayload` |
| `"build_started"` | `BUILD_STARTED` | `BuildStartedPayload` |
| `"build_progress"` | `BUILD_PROGRESS` | `BuildProgressPayload` |
| `"build_complete"` | `BUILD_COMPLETE` | `BuildCompletePayload` |
| `"build_failed"` | `BUILD_FAILED` | `BuildFailedPayload` |

### Agent Domain

| Value | Constant | Payload Class |
|-------|----------|---------------|
| `"status"` | `STATUS` | `AgentStatusPayload` |
| `"approval_request"` | `APPROVAL_REQUEST` | `ApprovalRequestPayload` |
| `"approval_response"` | `APPROVAL_RESPONSE` | `ApprovalResponsePayload` |
| `"command"` | `COMMAND` | `CommandPayload` |
| `"result"` | `RESULT` | `ResultPayload` |
| `"error"` | `ERROR` | `AgentStatusPayload` (state=error) |

### Jarvis Domain

| Value | Constant | Payload Class |
|-------|----------|---------------|
| `"intent_classified"` | `INTENT_CLASSIFIED` | `IntentClassifiedPayload` |
| `"dispatch"` | `DISPATCH` | `DispatchPayload` |
| `"agent_result"` | `AGENT_RESULT` | `AgentResultPayload` |
| `"notification"` | `NOTIFICATION` | `NotificationPayload` |

### Fleet Domain

| Value | Constant | Payload Class |
|-------|----------|---------------|
| `"agent_register"` | `AGENT_REGISTER` | `AgentManifest` |
| `"agent_heartbeat"` | `AGENT_HEARTBEAT` | `AgentHeartbeatPayload` |
| `"agent_deregister"` | `AGENT_DEREGISTER` | `AgentDeregistrationPayload` |

---

## Key Payload Schemas

### FeatureReadyForBuildPayload (NEW -- replaces ReadyForDevPayload)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `feature_id` | `str` | (required) | Feature identifier |
| `spec_path` | `str` | (required) | Path to feature spec YAML |
| `plan_path` | `str` | (required) | Path to feature plan |
| `pipeline_type` | `Literal["greenfield", "existing"]` | (required) | Pipeline type |
| `source_commands` | `list[str]` | `[]` | GuardKit commands that produced the spec |

**Publisher:** Pipeline Orchestrator Agent (after completing GuardKit command sequence)

### BuildProgressPayload

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `feature_id` | `str` | | Feature identifier |
| `build_id` | `str` | Pattern: `build-{feature_id}-{YYYYMMDDHHMMSS}` | Build identifier |
| `wave` | `int` | `ge=1` | Current wave number |
| `wave_total` | `int` | `ge=1` | Total wave count |
| `overall_progress_pct` | `float` | `ge=0.0, le=100.0` | Progress percentage |
| `elapsed_seconds` | `int` | `ge=0` | Elapsed time |

### ApprovalRequestPayload

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `request_id` | `str` | (required) | Unique request ID |
| `agent_id` | `str` | (required) | Requesting agent |
| `action_description` | `str` | (required) | What approval is for |
| `risk_level` | `Literal["low", "medium", "high"]` | (required) | Risk classification |
| `details` | `dict[str, Any]` | (required) | Action details |
| `timeout_seconds` | `int` | `300` | Approval timeout |

---

## Invariants

1. Every `EventType` value MUST have a corresponding Pydantic payload class
2. `MessageEnvelope.extra = "ignore"` -- always tolerate unknown fields
3. New payload fields MUST be optional with defaults (ADR-002)
4. `build_id` format: `build-{feature_id}-{YYYYMMDDHHMMSS}`
5. `overall_progress_pct` constrained to 0.0-100.0
6. `confidence` fields constrained to 0.0-1.0

---

## Relationships

```
MessageEnvelope
  |-- contains --> EventType (discriminator)
  |-- carries  --> *Payload (one per EventType)
  |-- scoped by --> project (multi-tenancy)
  |-- linked by --> correlation_id
```
