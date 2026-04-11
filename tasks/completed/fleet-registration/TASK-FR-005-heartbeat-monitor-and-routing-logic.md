---
id: TASK-FR-005
title: Heartbeat monitor and routing logic
status: completed
task_type: feature
priority: high
created: 2026-04-08 00:00:00+00:00
updated: '2026-04-11T00:00:00+00:00'
complexity: 6
parent_review: TASK-B5F3
feature_id: FEAT-FR01
wave: 4
implementation_mode: task-work
dependencies:
- TASK-FR-003
consumer_context:
- task: TASK-FR-003
  consumes: ManifestRegistry
  framework: ABC from nats_core.manifest
  driver: abc.ABC
  format_note: "Import as: from nats_core.manifest import ManifestRegistry \u2014\
    \ routing functions accept a ManifestRegistry instance and call list_all() and\
    \ find_by_intent()"
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/nats-core/.guardkit/worktrees/FEAT-BEA5
  base_branch: main
  started_at: '2026-04-08T23:34:02.971832'
  last_updated: '2026-04-08T23:39:43.698386'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-08T23:34:02.971832'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
completed: '2026-04-11T00:00:00+00:00'
completed_location: tasks/completed/fleet-registration/
---

# TASK-FR-005: Heartbeat monitor and routing logic

## Description

Implement the routing engine and heartbeat liveness monitor as pure functions in
`src/nats_core/_routing.py`. No I/O in routing functions — they take data and return
decisions. The heartbeat monitor is an async function that checks liveness.

## Routing Logic

### `src/nats_core/_routing.py`

```python
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from nats_core.manifest import AgentManifest, ManifestRegistry

logger = logging.getLogger(__name__)

HEARTBEAT_TIMEOUT_SECONDS = 90


@dataclass
class HeartbeatRecord:
    """Tracks liveness state for a registered agent."""
    agent_id: str
    last_seen: float = field(default_factory=time.monotonic)
    queue_depth: int = 0
    active_tasks: int = 0
    available: bool = True


def select_agent(
    candidates: list[AgentManifest],
    intent: str,
    heartbeats: dict[str, HeartbeatRecord],
) -> AgentManifest | None:
    """Select the best agent for a given intent.

    Algorithm:
      1. Filter by intent pattern match
      2. Filter by availability (heartbeat not timed out)
      3. Filter by capacity (active_tasks < max_concurrent)
      4. Sort by confidence descending, then queue_depth ascending (tiebreak)
      5. Return first result, or None if no eligible agent

    Args:
        candidates: All registered manifests.
        intent: The classified intent pattern to route.
        heartbeats: Liveness records keyed by agent_id.

    Returns:
        The selected AgentManifest, or None if no capable agent is available.
    """
    eligible = [
        m for m in candidates
        if any(cap.pattern == intent for cap in m.intents)
        and heartbeats.get(m.agent_id, HeartbeatRecord(m.agent_id)).available
        and _has_capacity(m, heartbeats)
    ]

    if not eligible:
        return None

    def sort_key(m: AgentManifest) -> tuple[float, int]:
        conf = max(
            (cap.confidence for cap in m.intents if cap.pattern == intent),
            default=0.0,
        )
        depth = heartbeats.get(m.agent_id, HeartbeatRecord(m.agent_id)).queue_depth
        return (-conf, depth)  # highest confidence first, lowest queue_depth second

    eligible.sort(key=sort_key)
    return eligible[0]


def _has_capacity(manifest: AgentManifest, heartbeats: dict[str, HeartbeatRecord]) -> bool:
    record = heartbeats.get(manifest.agent_id)
    if record is None:
        return True  # No heartbeat yet — assume available (just registered)
    return record.active_tasks < manifest.max_concurrent


def record_heartbeat(
    agent_id: str,
    queue_depth: int,
    active_tasks: int,
    heartbeats: dict[str, HeartbeatRecord],
) -> None:
    """Update the heartbeat record for an agent. Creates entry if not present."""
    record = heartbeats.get(agent_id)
    if record is None:
        heartbeats[agent_id] = HeartbeatRecord(
            agent_id=agent_id,
            queue_depth=queue_depth,
            active_tasks=active_tasks,
        )
    else:
        record.last_seen = time.monotonic()
        record.queue_depth = queue_depth
        record.active_tasks = active_tasks
        record.available = True


def check_timeouts(
    heartbeats: dict[str, HeartbeatRecord],
    timeout: float = HEARTBEAT_TIMEOUT_SECONDS,
) -> list[str]:
    """Mark agents as unavailable if their heartbeat has timed out.

    Returns:
        List of agent_ids that were newly marked unavailable.
    """
    now = time.monotonic()
    timed_out: list[str] = []
    for record in heartbeats.values():
        if record.available and (now - record.last_seen) >= timeout:
            record.available = False
            timed_out.append(record.agent_id)
            logger.warning("heartbeat timeout: agent %s marked unavailable", record.agent_id)
    return timed_out
```

## Acceptance Criteria

- [ ] `select_agent()` returns the agent with highest confidence for the requested intent
- [ ] `select_agent()` breaks confidence ties using `queue_depth` ascending (lower queue preferred)
- [ ] `select_agent()` skips agents where `active_tasks >= max_concurrent`
- [ ] `select_agent()` skips agents marked `available=False` in heartbeat records
- [ ] `select_agent()` returns `None` when no eligible agent exists (empty fleet or all filtered)
- [ ] `record_heartbeat()` creates a new `HeartbeatRecord` if `agent_id` not in `heartbeats`
- [ ] `record_heartbeat()` resets `available=True` when a heartbeat arrives (recovery from timeout)
- [ ] `check_timeouts()` marks agents unavailable when `now - last_seen >= 90s`
- [ ] `check_timeouts()` returns the list of newly timed-out `agent_id`s
- [ ] An agent at exactly 89s since last heartbeat is NOT timed out
- [ ] An agent at exactly 90s since last heartbeat IS timed out
- [ ] All routing functions are pure (no I/O, no NATS calls)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Implementation Notes

- `time.monotonic()` used for timeout arithmetic — never `datetime.now()` (avoids clock drift)
- `check_timeouts()` does not deregister from the registry — that is the caller's responsibility
- Recovery scenario: agent resumes heartbeating after timeout → `record_heartbeat()` sets `available=True`
- `select_agent()` receives `candidates` (all manifests) — the caller queries the registry

## Seam Tests

The following seam test validates the integration contract with TASK-FR-003. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify ManifestRegistry interface contract from TASK-FR-003."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("ManifestRegistry")
async def test_routing_accepts_manifest_registry_list_all():
    """Verify routing logic can call ManifestRegistry.list_all() and consume results.

    Contract: ManifestRegistry ABC from nats_core.manifest — list_all() returns list[AgentManifest]
    Producer: TASK-FR-003
    """
    from nats_core.manifest import AgentManifest, IntentCapability, InMemoryManifestRegistry
    from nats_core._routing import select_agent, HeartbeatRecord

    registry = InMemoryManifestRegistry()
    manifest = AgentManifest(
        agent_id="test-agent",
        name="Test Agent",
        template="base",
        intents=[IntentCapability(pattern="test.intent", confidence=0.9, description="test")],
    )
    await registry.register(manifest)

    candidates = await registry.list_all()
    heartbeats: dict[str, HeartbeatRecord] = {}

    result = select_agent(candidates, "test.intent", heartbeats)
    assert result is not None
    assert result.agent_id == "test-agent"
```
