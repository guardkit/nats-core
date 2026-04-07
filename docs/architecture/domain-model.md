# nats-core Domain Model

## Core Entities

### MessageEnvelope

The base wire format for all NATS messages in the fleet.

| Field | Type | Description |
|-------|------|-------------|
| message_id | str (UUID v4) | Unique message identifier (auto-generated) |
| timestamp | datetime (UTC) | Message creation time (auto-generated) |
| version | str | Schema version (default "1.0") |
| source_id | str | Originating service/agent identifier |
| event_type | EventType | Discriminator for payload type |
| project | str or None | Project scope for multi-tenancy |
| correlation_id | str or None | Links related messages across the fleet |
| payload | dict | Event-specific payload data |

### EventType (Enum)

Discriminator enum with four domains:

- **Pipeline:** FEATURE_PLANNED, READY_FOR_DEV, BUILD_STARTED, BUILD_PROGRESS, BUILD_COMPLETE, BUILD_FAILED, TICKET_UPDATED
- **Agent:** STATUS, APPROVAL_REQUEST, APPROVAL_RESPONSE, COMMAND, RESULT, ERROR
- **Jarvis:** INTENT_CLASSIFIED, DISPATCH, AGENT_RESULT, NOTIFICATION
- **Fleet:** AGENT_REGISTER, AGENT_DEREGISTER, AGENT_HEARTBEAT

## Event Domain: Pipeline

Events tracking the software build lifecycle.

| Payload Model | Key Fields |
|--------------|------------|
| FeaturePlannedPayload | feature_id, repo, wave_count, task_count |
| BuildProgressPayload | feature_id, build_id, wave, overall_progress_pct |
| BuildCompletePayload | feature_id, build_id, pr_url, duration_seconds |
| BuildFailedPayload | feature_id, build_id, failure_reason, recoverable |

## Event Domain: Agent

Events for agent status, approval workflows, and command/result patterns.

| Payload Model | Key Fields |
|--------------|------------|
| AgentStatusPayload | state (running/idle/awaiting_approval/error/paused) |
| ApprovalRequestPayload | request_id, agent_id, risk_level, timeout_seconds |
| ApprovalResponsePayload | request_id, decision (approve/reject/defer/override) |

## Event Domain: Jarvis

Events for intent routing and dispatch.

| Payload Model | Key Fields |
|--------------|------------|
| IntentClassifiedPayload | intent, confidence, target_agent, adapter_source |
| DispatchPayload | target_agent, intent, correlation_id |

## Event Domain: Fleet Registration

CAN bus pattern -- agents self-announce capabilities on startup.

| Payload Model | Key Fields |
|--------------|------------|
| AgentRegistrationPayload | agent_id, name, intents (IntentCapability[]), max_concurrent |
| AgentHeartbeatPayload | agent_id, status, queue_depth, active_tasks, uptime_seconds |
| AgentDeregistrationPayload | agent_id, reason |

### IntentCapability

Describes a single intent an agent can handle.

| Field | Type | Description |
|-------|------|-------------|
| pattern | str | Intent pattern (e.g., "software.build", "ideate") |
| signals | list[str] | Signal words for intent matching |
| confidence | float (0.0-1.0) | How well this agent handles this intent |
| description | str | Human-readable description |

## Topic Structure

Hierarchical NATS subjects organised by domain:

```
pipeline.{event}.{feature_id}      -- Build lifecycle
agents.status.{agent_id}           -- Agent status
agents.approval.{agent_id}.{task_id} -- Approval workflow
agents.{agent_id}.tools.{tool_name} -- Agent-to-agent tool calls
fleet.register                     -- Agent registration
fleet.heartbeat.{agent_id}         -- Agent liveness
jarvis.command.{adapter}           -- Inbound commands
jarvis.dispatch.{agent}            -- Outbound dispatch
```

Multi-tenancy: `Topics.for_project("finproxy", topic)` prefixes with project scope.

## Relationships

```
MessageEnvelope
  |-- contains --> EventType (discriminator)
  |-- carries  --> *Payload (one per EventType)
  |-- scoped by --> project (multi-tenancy)
  |-- linked by --> correlation_id

AgentRegistrationPayload
  |-- declares --> IntentCapability[] (capabilities)
  |-- published to --> fleet.register topic
  |-- stored in --> NATS KV (agent-registry bucket)

AgentHeartbeatPayload
  |-- published to --> fleet.heartbeat.{agent_id}
  |-- monitored by --> Jarvis Router (timeout = 90s)
```
