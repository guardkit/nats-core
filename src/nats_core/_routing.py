"""Routing engine and heartbeat liveness monitor for the nats-core fleet.

Pure functions that take data and return routing decisions — no I/O, no NATS
calls.  The heartbeat monitor tracks agent liveness via monotonic timestamps
so clock-drift cannot cause false timeouts.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from nats_core.manifest import AgentManifest

logger = logging.getLogger(__name__)

HEARTBEAT_TIMEOUT_SECONDS: float = 90


@dataclass
class HeartbeatRecord:
    """Tracks liveness state for a registered agent.

    Attributes:
        agent_id: Kebab-case agent identifier.
        last_seen: Monotonic timestamp of the last heartbeat.
        queue_depth: Number of messages queued for the agent.
        active_tasks: Number of tasks currently being processed.
        available: Whether the agent is considered live.
    """

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
      1. Filter by intent pattern match (exact match on IntentCapability.pattern).
      2. Filter by availability (heartbeat not timed out).
      3. Filter by capacity (active_tasks < max_concurrent).
      4. Sort by confidence descending, then queue_depth ascending (tiebreak).
      5. Return first result, or None if no eligible agent.

    Args:
        candidates: All registered manifests.
        intent: The classified intent pattern to route.
        heartbeats: Liveness records keyed by agent_id.

    Returns:
        The selected AgentManifest, or None if no capable agent is available.
    """
    eligible = [
        m
        for m in candidates
        if any(cap.pattern == intent for cap in m.intents)
        and heartbeats.get(m.agent_id, HeartbeatRecord(m.agent_id)).available
        and _has_capacity(m, heartbeats)
    ]

    if not eligible:
        return None

    def _sort_key(m: AgentManifest) -> tuple[float, int]:
        conf = max(
            (cap.confidence for cap in m.intents if cap.pattern == intent),
            default=0.0,
        )
        depth = heartbeats.get(m.agent_id, HeartbeatRecord(m.agent_id)).queue_depth
        return (-conf, depth)  # highest confidence first, lowest queue_depth second

    eligible.sort(key=_sort_key)
    return eligible[0]


def _has_capacity(
    manifest: AgentManifest,
    heartbeats: dict[str, HeartbeatRecord],
) -> bool:
    """Check whether an agent has capacity to accept another task.

    Args:
        manifest: The agent manifest to check.
        heartbeats: Liveness records keyed by agent_id.

    Returns:
        True if the agent has remaining capacity, False otherwise.
    """
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
    """Update the heartbeat record for an agent. Creates entry if not present.

    When a heartbeat arrives for an agent previously marked unavailable, this
    function resets ``available=True`` (recovery from timeout).

    Args:
        agent_id: The agent identifier.
        queue_depth: Current queue depth reported by the agent.
        active_tasks: Current active task count reported by the agent.
        heartbeats: Mutable mapping of heartbeat records to update in place.
    """
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

    Uses ``time.monotonic()`` for timeout arithmetic to avoid clock-drift
    issues.  Does **not** deregister from the manifest registry — that is the
    caller's responsibility.

    Args:
        heartbeats: Mutable mapping of heartbeat records to check.
        timeout: Seconds after which an agent is considered timed out.

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
