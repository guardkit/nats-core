"""Tests for heartbeat monitor and routing logic (_routing module).

Covers all acceptance criteria from TASK-FR-005:
- select_agent() routing by intent, confidence, capacity, availability
- record_heartbeat() creation and recovery
- check_timeouts() liveness detection with exact boundary tests
- Seam test for ManifestRegistry integration contract
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from nats_core._routing import (
    HEARTBEAT_TIMEOUT_SECONDS,
    HeartbeatRecord,
    check_timeouts,
    record_heartbeat,
    select_agent,
)
from nats_core.manifest import (
    AgentManifest,
    InMemoryManifestRegistry,
    IntentCapability,
)

# ---------------------------------------------------------------------------
# Factory helpers (local to this test module)
# ---------------------------------------------------------------------------


def _make_manifest(
    agent_id: str = "agent-a",
    pattern: str = "code.review",
    confidence: float = 0.9,
    max_concurrent: int = 2,
) -> AgentManifest:
    """Create an AgentManifest with a single intent capability."""
    return AgentManifest(
        agent_id=agent_id,
        name=f"Agent {agent_id}",
        template="base",
        intents=[
            IntentCapability(
                pattern=pattern,
                confidence=confidence,
                description=f"Handles {pattern}",
            )
        ],
        max_concurrent=max_concurrent,
    )


def _make_heartbeat(
    agent_id: str = "agent-a",
    last_seen: float | None = None,
    queue_depth: int = 0,
    active_tasks: int = 0,
    available: bool = True,
) -> HeartbeatRecord:
    """Create a HeartbeatRecord with explicit or default values."""
    return HeartbeatRecord(
        agent_id=agent_id,
        last_seen=last_seen if last_seen is not None else time.monotonic(),
        queue_depth=queue_depth,
        active_tasks=active_tasks,
        available=available,
    )


# ===========================================================================
# select_agent tests
# ===========================================================================


class TestSelectAgent:
    """Tests for the select_agent() routing function."""

    @pytest.mark.unit
    def test_returns_agent_with_highest_confidence(self) -> None:
        """AC: select_agent() returns agent with highest confidence for requested intent."""
        low = _make_manifest(agent_id="agent-low", confidence=0.5)
        high = _make_manifest(agent_id="agent-high", confidence=0.95)
        heartbeats = {
            "agent-low": _make_heartbeat(agent_id="agent-low"),
            "agent-high": _make_heartbeat(agent_id="agent-high"),
        }

        result = select_agent([low, high], "code.review", heartbeats)

        assert result is not None
        assert result.agent_id == "agent-high"

    @pytest.mark.unit
    def test_breaks_confidence_tie_by_queue_depth(self) -> None:
        """AC: select_agent() breaks confidence ties using queue_depth ascending."""
        a = _make_manifest(agent_id="agent-a", confidence=0.9)
        b = _make_manifest(agent_id="agent-b", confidence=0.9)
        heartbeats = {
            "agent-a": _make_heartbeat(agent_id="agent-a", queue_depth=5),
            "agent-b": _make_heartbeat(agent_id="agent-b", queue_depth=1),
        }

        result = select_agent([a, b], "code.review", heartbeats)

        assert result is not None
        assert result.agent_id == "agent-b"

    @pytest.mark.unit
    def test_skips_agents_at_capacity(self) -> None:
        """AC: select_agent() skips agents where active_tasks >= max_concurrent."""
        full = _make_manifest(agent_id="agent-full", max_concurrent=2)
        free = _make_manifest(agent_id="agent-free", confidence=0.8, max_concurrent=2)
        heartbeats = {
            "agent-full": _make_heartbeat(agent_id="agent-full", active_tasks=2),
            "agent-free": _make_heartbeat(agent_id="agent-free", active_tasks=1),
        }

        result = select_agent([full, free], "code.review", heartbeats)

        assert result is not None
        assert result.agent_id == "agent-free"

    @pytest.mark.unit
    def test_skips_unavailable_agents(self) -> None:
        """AC: select_agent() skips agents marked available=False."""
        down = _make_manifest(agent_id="agent-down", confidence=0.99)
        up = _make_manifest(agent_id="agent-up", confidence=0.7)
        heartbeats = {
            "agent-down": _make_heartbeat(agent_id="agent-down", available=False),
            "agent-up": _make_heartbeat(agent_id="agent-up"),
        }

        result = select_agent([down, up], "code.review", heartbeats)

        assert result is not None
        assert result.agent_id == "agent-up"

    @pytest.mark.unit
    def test_returns_none_when_no_eligible_agent(self) -> None:
        """AC: select_agent() returns None when no eligible agent exists."""
        result = select_agent([], "code.review", {})
        assert result is None

    @pytest.mark.unit
    def test_returns_none_when_all_agents_filtered(self) -> None:
        """AC: select_agent() returns None when all agents are filtered out."""
        agent = _make_manifest(agent_id="agent-a", pattern="other.intent")
        heartbeats = {"agent-a": _make_heartbeat(agent_id="agent-a")}

        result = select_agent([agent], "code.review", heartbeats)
        assert result is None

    @pytest.mark.unit
    def test_agent_without_heartbeat_is_assumed_available(self) -> None:
        """Agent with no heartbeat record is treated as available with capacity."""
        agent = _make_manifest(agent_id="agent-new")
        heartbeats: dict[str, HeartbeatRecord] = {}

        result = select_agent([agent], "code.review", heartbeats)

        assert result is not None
        assert result.agent_id == "agent-new"

    @pytest.mark.unit
    @pytest.mark.key_example
    def test_full_routing_scenario(self) -> None:
        """End-to-end: three agents, one down, one at capacity, one available."""
        down = _make_manifest(agent_id="agent-down", confidence=0.99)
        full = _make_manifest(agent_id="agent-full", confidence=0.95, max_concurrent=1)
        good = _make_manifest(agent_id="agent-good", confidence=0.8)

        heartbeats = {
            "agent-down": _make_heartbeat(agent_id="agent-down", available=False),
            "agent-full": _make_heartbeat(agent_id="agent-full", active_tasks=1),
            "agent-good": _make_heartbeat(agent_id="agent-good", queue_depth=2),
        }

        result = select_agent([down, full, good], "code.review", heartbeats)

        assert result is not None
        assert result.agent_id == "agent-good"

    @pytest.mark.unit
    def test_filters_by_intent_pattern_exact_match(self) -> None:
        """Only agents with exact intent pattern match are considered."""
        matching = _make_manifest(agent_id="agent-match", pattern="code.review")
        other = _make_manifest(agent_id="agent-other", pattern="code.deploy")
        heartbeats = {
            "agent-match": _make_heartbeat(agent_id="agent-match"),
            "agent-other": _make_heartbeat(agent_id="agent-other"),
        }

        result = select_agent([matching, other], "code.review", heartbeats)

        assert result is not None
        assert result.agent_id == "agent-match"


# ===========================================================================
# record_heartbeat tests
# ===========================================================================


class TestRecordHeartbeat:
    """Tests for the record_heartbeat() function."""

    @pytest.mark.unit
    def test_creates_new_heartbeat_record(self) -> None:
        """AC: record_heartbeat() creates a new HeartbeatRecord if agent_id not present."""
        heartbeats: dict[str, HeartbeatRecord] = {}

        record_heartbeat("agent-new", queue_depth=3, active_tasks=1, heartbeats=heartbeats)

        assert "agent-new" in heartbeats
        record = heartbeats["agent-new"]
        assert record.agent_id == "agent-new"
        assert record.queue_depth == 3
        assert record.active_tasks == 1
        assert record.available is True

    @pytest.mark.unit
    def test_updates_existing_heartbeat(self) -> None:
        """Existing heartbeat record is updated with new values."""
        heartbeats: dict[str, HeartbeatRecord] = {
            "agent-a": _make_heartbeat(agent_id="agent-a", queue_depth=0, active_tasks=0),
        }
        old_last_seen = heartbeats["agent-a"].last_seen

        record_heartbeat("agent-a", queue_depth=5, active_tasks=2, heartbeats=heartbeats)

        record = heartbeats["agent-a"]
        assert record.queue_depth == 5
        assert record.active_tasks == 2
        assert record.last_seen >= old_last_seen

    @pytest.mark.unit
    def test_recovery_resets_available_true(self) -> None:
        """AC: record_heartbeat() resets available=True when heartbeat arrives (recovery)."""
        heartbeats: dict[str, HeartbeatRecord] = {
            "agent-a": _make_heartbeat(agent_id="agent-a", available=False),
        }

        record_heartbeat("agent-a", queue_depth=0, active_tasks=0, heartbeats=heartbeats)

        assert heartbeats["agent-a"].available is True


# ===========================================================================
# check_timeouts tests
# ===========================================================================


class TestCheckTimeouts:
    """Tests for the check_timeouts() function."""

    @pytest.mark.unit
    def test_marks_agent_unavailable_after_timeout(self) -> None:
        """AC: check_timeouts() marks agents unavailable when now - last_seen >= 90s."""
        old_time = time.monotonic() - 100  # 100s ago — well past timeout
        heartbeats: dict[str, HeartbeatRecord] = {
            "agent-stale": _make_heartbeat(
                agent_id="agent-stale", last_seen=old_time, available=True
            ),
        }

        timed_out = check_timeouts(heartbeats)

        assert "agent-stale" in timed_out
        assert heartbeats["agent-stale"].available is False

    @pytest.mark.unit
    def test_returns_newly_timed_out_ids(self) -> None:
        """AC: check_timeouts() returns list of newly timed-out agent_ids."""
        old = time.monotonic() - 100
        heartbeats: dict[str, HeartbeatRecord] = {
            "agent-stale": _make_heartbeat(agent_id="agent-stale", last_seen=old),
            "agent-fresh": _make_heartbeat(agent_id="agent-fresh"),
        }

        timed_out = check_timeouts(heartbeats)

        assert timed_out == ["agent-stale"]

    @pytest.mark.unit
    def test_already_unavailable_not_reported(self) -> None:
        """Agents already marked unavailable are not reported again."""
        old = time.monotonic() - 100
        heartbeats: dict[str, HeartbeatRecord] = {
            "agent-already-down": _make_heartbeat(
                agent_id="agent-already-down", last_seen=old, available=False
            ),
        }

        timed_out = check_timeouts(heartbeats)

        assert timed_out == []

    @pytest.mark.unit
    @pytest.mark.boundary
    def test_agent_at_89s_is_not_timed_out(self) -> None:
        """AC: An agent at exactly 89s since last heartbeat is NOT timed out."""
        now = time.monotonic()
        heartbeats: dict[str, HeartbeatRecord] = {
            "agent-a": _make_heartbeat(agent_id="agent-a", last_seen=now - 89),
        }

        with patch("nats_core._routing.time") as mock_time:
            mock_time.monotonic.return_value = now
            timed_out = check_timeouts(heartbeats)

        assert timed_out == []
        assert heartbeats["agent-a"].available is True

    @pytest.mark.unit
    @pytest.mark.boundary
    def test_agent_at_90s_is_timed_out(self) -> None:
        """AC: An agent at exactly 90s since last heartbeat IS timed out."""
        now = time.monotonic()
        heartbeats: dict[str, HeartbeatRecord] = {
            "agent-a": _make_heartbeat(agent_id="agent-a", last_seen=now - 90),
        }

        with patch("nats_core._routing.time") as mock_time:
            mock_time.monotonic.return_value = now
            timed_out = check_timeouts(heartbeats)

        assert timed_out == ["agent-a"]
        assert heartbeats["agent-a"].available is False

    @pytest.mark.unit
    def test_custom_timeout_value(self) -> None:
        """Custom timeout value is respected."""
        old = time.monotonic() - 50
        heartbeats: dict[str, HeartbeatRecord] = {
            "agent-a": _make_heartbeat(agent_id="agent-a", last_seen=old),
        }

        timed_out = check_timeouts(heartbeats, timeout=30)

        assert "agent-a" in timed_out

    @pytest.mark.unit
    @pytest.mark.edge_case
    def test_empty_heartbeats(self) -> None:
        """check_timeouts() with empty heartbeats returns empty list."""
        assert check_timeouts({}) == []


# ===========================================================================
# HeartbeatRecord tests
# ===========================================================================


class TestHeartbeatRecord:
    """Tests for the HeartbeatRecord dataclass."""

    @pytest.mark.unit
    def test_default_factory_uses_monotonic(self) -> None:
        """Default last_seen uses time.monotonic()."""
        before = time.monotonic()
        record = HeartbeatRecord(agent_id="agent-a")
        after = time.monotonic()

        assert before <= record.last_seen <= after

    @pytest.mark.unit
    def test_default_values(self) -> None:
        """All defaults are sensible."""
        record = HeartbeatRecord(agent_id="agent-a")

        assert record.queue_depth == 0
        assert record.active_tasks == 0
        assert record.available is True


# ===========================================================================
# Constants
# ===========================================================================


class TestConstants:
    """Tests for module-level constants."""

    @pytest.mark.unit
    def test_heartbeat_timeout_is_90(self) -> None:
        """Default heartbeat timeout is 90 seconds."""
        assert HEARTBEAT_TIMEOUT_SECONDS == 90


# ===========================================================================
# Purity checks — routing functions do no I/O
# ===========================================================================


class TestPurity:
    """AC: All routing functions are pure (no I/O, no NATS calls)."""

    @pytest.mark.unit
    def test_select_agent_is_synchronous(self) -> None:
        """select_agent is a regular (non-async) function."""
        import inspect
        assert not inspect.iscoroutinefunction(select_agent)

    @pytest.mark.unit
    def test_record_heartbeat_is_synchronous(self) -> None:
        """record_heartbeat is a regular (non-async) function."""
        import inspect
        assert not inspect.iscoroutinefunction(record_heartbeat)

    @pytest.mark.unit
    def test_check_timeouts_is_synchronous(self) -> None:
        """check_timeouts is a regular (non-async) function."""
        import inspect
        assert not inspect.iscoroutinefunction(check_timeouts)


# ===========================================================================
# Seam test — ManifestRegistry contract integration
# ===========================================================================


@pytest.mark.seam
@pytest.mark.integration_contract("ManifestRegistry")
async def test_routing_accepts_manifest_registry_list_all() -> None:
    """Verify routing logic can call ManifestRegistry.list_all() and consume results.

    Contract: ManifestRegistry ABC from nats_core.manifest — list_all() returns list[AgentManifest]
    Producer: TASK-FR-003
    """
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
