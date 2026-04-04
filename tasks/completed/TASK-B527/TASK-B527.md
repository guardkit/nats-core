---
id: TASK-B527
title: Merge fleet registration addendum into parent spec
status: completed
created: 2026-04-04T00:00:00Z
updated: 2026-04-04T00:00:00Z
completed: 2026-04-04T00:00:00Z
completed_location: tasks/completed/TASK-B527/
priority: high
tags: [documentation, fleet, spec-merge]
complexity: 5
task_type: feature
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-04T00:00:00Z
---

# Task: Merge fleet registration addendum into parent spec

## Description

Read both spec files and merge the addendum content into the parent spec following the explicit merge instructions:

- `docs/design/specs/nats-core-system-spec.md` (parent)
- `docs/design/specs/nats-core-spec-addendum-fleet-registration.md` (addendum)

## Acceptance Criteria

### From Addendum Merge Instructions
- [x] Add `fleet.py` to the package structure under `events/` in the repo structure section
- [x] Add 3 new EventType values (`AGENT_REGISTER`, `AGENT_DEREGISTER`, `AGENT_HEARTBEAT`) to the EventType enum in Feature 2
- [x] Add Fleet registration schemas (`IntentCapability`, `AgentRegistrationPayload`, `AgentHeartbeatPayload`, `AgentDeregistrationPayload`) to Key Payload Schemas in Feature 2
- [x] Add `Topics.Fleet` (`REGISTER`, `DEREGISTER`, `HEARTBEAT`, `HEARTBEAT_ALL`, `ALL`) to Topic Registry in Feature 3
- [x] Add entire Feature 6 section (Fleet Registration with design principles, lifecycle, routing decision, BDD acceptance criteria) as new feature section before Non-Functional Requirements
- [x] Add fleet convenience methods (`register_agent`, `deregister_agent`, `heartbeat`, `get_fleet_registry`, `watch_fleet`) to NATSClient in Feature 4

### Additional Elements (post-addendum design)
- [x] Add `agents.{agent_id}.tools.{tool_name}` and `agents.{agent_id}.tools.>` to Topics under a new `Topics.Agents` class alongside `Topics.Fleet` — for direct agent-to-agent tool invocation
- [x] Add `call_agent_tool(agent_id, tool_name, params)` convenience method to NATSClient in Feature 4
- [x] Add `manifest.py` to the top level of `nats_core/` in the package structure — holds `AgentManifest`, `ToolCapability`, `IntentCapability` (see `docs/design/contracts/agent-manifest-contract.md` for schema)

### Post-Merge Verification
- [x] Document reads as one coherent spec with no duplicate sections
- [x] Delete addendum file `nats-core-spec-addendum-fleet-registration.md`
- [x] Commit with message: "Merge fleet registration addendum into system spec, add agent tool topics and manifest"

## Implementation Notes

- The addendum file has explicit merge instructions at the top — follow them precisely
- Reference `docs/design/contracts/agent-manifest-contract.md` for the manifest schema when adding `manifest.py` to the package structure
- The `Topics.Agents` class is new and was not in the original addendum

## Test Requirements

- [x] Verify no duplicate sections in merged spec
- [x] Verify all addendum content is present in parent spec
- [x] Verify addendum file is deleted after merge
