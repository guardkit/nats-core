---
id: TASK-B527
title: Merge fleet registration addendum into parent spec
status: in_review
created: 2026-04-04T00:00:00Z
updated: 2026-04-04T00:00:00Z
priority: high
tags: [documentation, fleet, spec-merge]
complexity: 5
task_type: feature
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Merge fleet registration addendum into parent spec

## Description

Read both spec files and merge the addendum content into the parent spec following the explicit merge instructions:

- `docs/design/specs/nats-core-system-spec.md` (parent)
- `docs/design/specs/nats-core-spec-addendum-fleet-registration.md` (addendum)

## Acceptance Criteria

### From Addendum Merge Instructions
- [ ] Add `fleet.py` to the package structure under `events/` in the repo structure section
- [ ] Add 3 new EventType values (`AGENT_REGISTER`, `AGENT_DEREGISTER`, `AGENT_HEARTBEAT`) to the EventType enum in Feature 2
- [ ] Add Fleet registration schemas (`IntentCapability`, `AgentRegistrationPayload`, `AgentHeartbeatPayload`, `AgentDeregistrationPayload`) to Key Payload Schemas in Feature 2
- [ ] Add `Topics.Fleet` (`REGISTER`, `DEREGISTER`, `HEARTBEAT`, `HEARTBEAT_ALL`, `ALL`) to Topic Registry in Feature 3
- [ ] Add entire Feature 6 section (Fleet Registration with design principles, lifecycle, routing decision, BDD acceptance criteria) as new feature section before Non-Functional Requirements
- [ ] Add fleet convenience methods (`register_agent`, `deregister_agent`, `heartbeat`, `get_fleet_registry`, `watch_fleet`) to NATSClient in Feature 4

### Additional Elements (post-addendum design)
- [ ] Add `agents.{agent_id}.tools.{tool_name}` and `agents.{agent_id}.tools.>` to Topics under a new `Topics.Agents` class alongside `Topics.Fleet` — for direct agent-to-agent tool invocation
- [ ] Add `call_agent_tool(agent_id, tool_name, params)` convenience method to NATSClient in Feature 4
- [ ] Add `manifest.py` to the top level of `nats_core/` in the package structure — holds `AgentManifest`, `ToolCapability`, `IntentCapability` (see `docs/design/contracts/agent-manifest-contract.md` for schema)

### Post-Merge Verification
- [ ] Document reads as one coherent spec with no duplicate sections
- [ ] Delete addendum file `nats-core-spec-addendum-fleet-registration.md`
- [ ] Commit with message: "Merge fleet registration addendum into system spec, add agent tool topics and manifest"

## Implementation Notes

- The addendum file has explicit merge instructions at the top — follow them precisely
- Reference `docs/design/contracts/agent-manifest-contract.md` for the manifest schema when adding `manifest.py` to the package structure
- The `Topics.Agents` class is new and was not in the original addendum

## Test Requirements

- [ ] Verify no duplicate sections in merged spec
- [ ] Verify all addendum content is present in parent spec
- [ ] Verify addendum file is deleted after merge
