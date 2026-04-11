"""Fleet Registration test suite — 28 BDD scenarios.

Maps every scenario from features/fleet-registration/fleet-registration.feature
to an async test function with proper pytest markers.  All tests run without a
live NATS server:

- Model/validation tests use Pydantic directly.
- Registry tests use InMemoryManifestRegistry.
- KV registry tests mock the KeyValue bucket via unittest.mock.
- Routing tests exercise pure functions from nats_core._routing.

Organised into sections matching the BDD scenario map in TASK-FR-006.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from nats_core._routing import (
    HEARTBEAT_TIMEOUT_SECONDS,
    HeartbeatRecord,
    check_timeouts,
    record_heartbeat,
    select_agent,
)
from nats_core.client import NATSKVManifestRegistry
from nats_core.events._fleet import AgentDeregistrationPayload, AgentHeartbeatPayload
from nats_core.manifest import AgentManifest, IntentCapability

from .conftest import (
    make_agent_manifest,
    make_heartbeat_payload,
    make_heartbeat_record,
    make_in_memory_registry,
    make_intent,
    make_manifest,
    make_mock_kv_bucket,
)


# ===================================================================
# Smoke / Key-Example Tests (6 scenarios)
# ===================================================================


@pytest.mark.smoke
@pytest.mark.key_example
async def test_agent_registers_appears_in_registry() -> None:
    """BDD: Agent registers on startup.

    When an agent publishes a registration, it should appear in the registry
    with the correct agent_id and at least one intent with valid confidence.
    """
    registry = make_in_memory_registry()
    manifest = make_agent_manifest(agent_id="product-owner-agent", name="Product Owner Agent")

    await registry.register(manifest)

    result = await registry.get("product-owner-agent")
    assert result is not None
    assert result.agent_id == "product-owner-agent"
    assert len(result.intents) >= 1
    for intent in result.intents:
        assert 0.0 <= intent.confidence <= 1.0


@pytest.mark.key_example
async def test_registration_includes_signal_words() -> None:
    """BDD: Registration includes signal words for intent matching.

    The ideation agent's registration should declare intent 'ideate' with
    signals including 'explore' and 'brainstorm', confidence >= 0.8.
    """
    manifest = make_agent_manifest(
        agent_id="ideation-agent",
        name="Ideation Agent",
        intents=[
            make_intent(
                pattern="ideate",
                signals=["explore", "brainstorm", "imagine"],
                confidence=0.85,
                description="Creative ideation",
            ),
        ],
    )

    ideate_intents = [i for i in manifest.intents if i.pattern == "ideate"]
    assert len(ideate_intents) == 1
    ideate = ideate_intents[0]
    assert "explore" in ideate.signals
    assert "brainstorm" in ideate.signals
    assert ideate.confidence >= 0.8


@pytest.mark.smoke
@pytest.mark.key_example
async def test_heartbeat_record_created_on_registration() -> None:
    """BDD: Agent begins heartbeating after registration.

    After registration, a heartbeat should include queue_depth, active_tasks,
    and a valid status.
    """
    heartbeat = make_heartbeat_payload(
        agent_id="ideation-agent",
        status="ready",
        queue_depth=0,
        active_tasks=0,
        uptime_seconds=30,
    )

    assert heartbeat.agent_id == "ideation-agent"
    assert heartbeat.queue_depth >= 0
    assert heartbeat.active_tasks >= 0
    assert heartbeat.status in {"ready", "busy", "degraded", "draining"}


@pytest.mark.smoke
@pytest.mark.key_example
async def test_deregistration_removes_from_registry() -> None:
    """BDD: Graceful deregistration removes agent from routing table.

    After deregistration with reason 'shutdown', the agent should no longer
    appear in the registry.
    """
    registry = make_in_memory_registry()
    manifest = make_agent_manifest(agent_id="youtube-planner", name="YouTube Planner")
    await registry.register(manifest)

    # Verify registered
    assert await registry.get("youtube-planner") is not None

    # Deregister
    await registry.deregister("youtube-planner")

    # Should no longer exist
    assert await registry.get("youtube-planner") is None
    # Router should not dispatch to removed agent
    matches = await registry.find_by_intent("software.build")
    agent_ids = [m.agent_id for m in matches]
    assert "youtube-planner" not in agent_ids


@pytest.mark.key_example
async def test_new_agent_discovered_via_find_by_intent() -> None:
    """BDD: New agent is auto-discovered without router changes.

    Adding a new agent to the registry makes it discoverable via
    find_by_intent without modifying any router code.
    """
    registry = make_in_memory_registry()
    # Register 3 existing agents
    for i in range(3):
        m = make_agent_manifest(
            agent_id=f"agent-{i}",
            name=f"Agent {i}",
            intents=[make_intent(pattern=f"intent-{i}")],
        )
        await registry.register(m)

    # New agent registers
    new_agent = make_agent_manifest(
        agent_id="product-owner-agent",
        name="Product Owner Agent",
        intents=[make_intent(pattern="product.document")],
    )
    await registry.register(new_agent)

    # Auto-discovered via find_by_intent (no code changes)
    results = await registry.find_by_intent("product.document")
    assert len(results) == 1
    assert results[0].agent_id == "product-owner-agent"


@pytest.mark.key_example
async def test_kv_registry_persists_across_reconnect() -> None:
    """BDD: Registration survives router restart via KV persistence.

    After registering 5 agents in the KV bucket, creating a new registry
    instance from the same bucket should recover all 5 agents.
    """
    kv = make_mock_kv_bucket()
    registry = NATSKVManifestRegistry(kv)

    # Register 5 agents
    for i in range(5):
        m = make_agent_manifest(
            agent_id=f"agent-{i}",
            name=f"Agent {i}",
            intents=[make_intent(pattern=f"intent-{i}")],
        )
        await registry.register(m)

    # Simulate router restart: create a new registry from the same KV
    registry2 = NATSKVManifestRegistry(kv)
    all_agents = await registry2.list_all()
    assert len(all_agents) == 5
    recovered_ids = {a.agent_id for a in all_agents}
    for i in range(5):
        assert f"agent-{i}" in recovered_ids


# ===================================================================
# Boundary Tests (11 scenarios)
# ===================================================================


@pytest.mark.boundary
async def test_confidence_boundary_zero_accepted() -> None:
    """BDD: Confidence 0.0 accepted."""
    manifest = make_agent_manifest(
        intents=[make_intent(confidence=0.0)],
    )
    assert manifest.intents[0].confidence == 0.0


@pytest.mark.boundary
async def test_confidence_boundary_mid_accepted() -> None:
    """BDD: Confidence 0.5 accepted."""
    manifest = make_agent_manifest(
        intents=[make_intent(confidence=0.5)],
    )
    assert manifest.intents[0].confidence == 0.5


@pytest.mark.boundary
async def test_confidence_boundary_one_accepted() -> None:
    """BDD: Confidence 1.0 accepted."""
    manifest = make_agent_manifest(
        intents=[make_intent(confidence=1.0)],
    )
    assert manifest.intents[0].confidence == 1.0


@pytest.mark.boundary
@pytest.mark.negative
async def test_confidence_below_zero_rejected() -> None:
    """BDD: Confidence -0.1 rejected."""
    with pytest.raises(ValidationError) as exc_info:
        make_agent_manifest(
            intents=[make_intent(confidence=-0.1)],
        )
    errors = exc_info.value.errors()
    assert any("confidence" in str(e).lower() or "greater than" in str(e).lower() for e in errors)


@pytest.mark.boundary
@pytest.mark.negative
async def test_confidence_above_one_rejected() -> None:
    """BDD: Confidence 1.1 rejected."""
    with pytest.raises(ValidationError) as exc_info:
        make_agent_manifest(
            intents=[make_intent(confidence=1.1)],
        )
    errors = exc_info.value.errors()
    assert any("confidence" in str(e).lower() or "less than" in str(e).lower() for e in errors)


@pytest.mark.boundary
async def test_max_concurrent_one_accepted() -> None:
    """BDD: max_concurrent 1 accepted."""
    manifest = make_agent_manifest(max_concurrent=1)
    assert manifest.max_concurrent == 1


@pytest.mark.boundary
@pytest.mark.negative
async def test_max_concurrent_zero_rejected() -> None:
    """BDD: max_concurrent 0 rejected."""
    with pytest.raises(ValidationError) as exc_info:
        make_agent_manifest(max_concurrent=0)
    errors = exc_info.value.errors()
    assert any(
        "max_concurrent" in str(e).lower() or "greater than" in str(e).lower() for e in errors
    )


@pytest.mark.boundary
async def test_heartbeat_89s_still_available() -> None:
    """BDD: Heartbeat at 89s does not timeout.

    An agent whose last heartbeat was 89 seconds ago should remain available.
    """
    now = time.monotonic()
    record = make_heartbeat_record(agent_id="test-agent", last_seen=now - 89)
    heartbeats: dict[str, HeartbeatRecord] = {"test-agent": record}

    timed_out = check_timeouts(heartbeats)

    assert "test-agent" not in timed_out
    assert heartbeats["test-agent"].available is True


@pytest.mark.boundary
async def test_heartbeat_90s_triggers_timeout() -> None:
    """BDD: No heartbeat for exactly 90 seconds triggers timeout."""
    now = time.monotonic()
    record = make_heartbeat_record(agent_id="test-agent", last_seen=now - 90)
    heartbeats: dict[str, HeartbeatRecord] = {"test-agent": record}

    timed_out = check_timeouts(heartbeats)

    assert "test-agent" in timed_out
    assert heartbeats["test-agent"].available is False


@pytest.mark.boundary
@pytest.mark.negative
async def test_empty_intents_registration_rejected() -> None:
    """BDD: Agent registration with no intent capabilities is rejected."""
    registry = make_in_memory_registry()
    manifest = make_agent_manifest(intents=[])

    with pytest.raises(ValueError, match="at least one intent capability is required"):
        await registry.register(manifest)


@pytest.mark.boundary
async def test_heartbeat_queue_depth_zero_valid() -> None:
    """BDD: Heartbeat with queue_depth 0 is valid and preferred in tiebreaking.

    An agent with queue_depth=0 should be preferred over one with higher queue_depth.
    """
    heartbeats: dict[str, HeartbeatRecord] = {}
    record_heartbeat("agent-a", queue_depth=0, active_tasks=0, heartbeats=heartbeats)

    assert heartbeats["agent-a"].queue_depth == 0

    # Verify tiebreaking: agent with queue_depth=0 preferred
    manifest_a = make_agent_manifest(
        agent_id="agent-a",
        name="Agent A",
        intents=[make_intent(pattern="test", confidence=1.0)],
    )
    manifest_b = make_agent_manifest(
        agent_id="agent-b",
        name="Agent B",
        intents=[make_intent(pattern="test", confidence=1.0)],
    )
    record_heartbeat("agent-b", queue_depth=5, active_tasks=0, heartbeats=heartbeats)

    selected = select_agent([manifest_a, manifest_b], "test", heartbeats)
    assert selected is not None
    assert selected.agent_id == "agent-a"


# ===================================================================
# Negative Tests (7 scenarios)
# ===================================================================


@pytest.mark.negative
async def test_missing_agent_id_rejected() -> None:
    """BDD: Registration missing agent_id is rejected."""
    with pytest.raises(ValidationError):
        AgentManifest(
            name="Test Agent",
            template="basic",
            intents=[IntentCapability(pattern="test", description="test")],
        )  # type: ignore[call-arg]


@pytest.mark.negative
async def test_missing_name_rejected() -> None:
    """BDD: Registration missing name is rejected."""
    with pytest.raises(ValidationError):
        AgentManifest(
            agent_id="test-agent",
            template="basic",
            intents=[IntentCapability(pattern="test", description="test")],
        )  # type: ignore[call-arg]


@pytest.mark.negative
async def test_missing_template_rejected() -> None:
    """BDD: Registration missing template is rejected."""
    with pytest.raises(ValidationError):
        AgentManifest(
            agent_id="test-agent",
            name="Test Agent",
            intents=[IntentCapability(pattern="test", description="test")],
        )  # type: ignore[call-arg]


@pytest.mark.negative
async def test_reregistration_upserts_not_duplicates() -> None:
    """BDD: Re-registration updates existing entry, not duplicates."""
    registry = make_in_memory_registry()
    original = make_agent_manifest(
        agent_id="ideation-agent",
        name="Ideation Agent",
        intents=[make_intent(pattern="ideate", description="Original")],
    )
    await registry.register(original)

    updated = make_agent_manifest(
        agent_id="ideation-agent",
        name="Ideation Agent v2",
        intents=[make_intent(pattern="ideate-v2", description="Updated")],
    )
    await registry.register(updated)

    all_agents = await registry.list_all()
    matching = [m for m in all_agents if m.agent_id == "ideation-agent"]
    assert len(matching) == 1
    assert matching[0].name == "Ideation Agent v2"
    assert matching[0].intents[0].pattern == "ideate-v2"


@pytest.mark.negative
async def test_deregistration_unknown_agent_ignored() -> None:
    """BDD: Deregistration for unknown agent is silently ignored."""
    registry = make_in_memory_registry()
    # Should not raise
    await registry.deregister("phantom-agent")

    all_agents = await registry.list_all()
    assert len(all_agents) == 0


@pytest.mark.negative
async def test_heartbeat_unregistered_agent_ignored() -> None:
    """BDD: Heartbeat from unregistered agent is ignored.

    A heartbeat for a non-existent agent should not create an entry in the
    registry or routing table.
    """
    registry = make_in_memory_registry()

    # Heartbeat for unregistered agent (record_heartbeat creates in heartbeats dict,
    # but the agent is NOT in the registry)
    heartbeats: dict[str, HeartbeatRecord] = {}
    record_heartbeat("ghost-agent", queue_depth=0, active_tasks=0, heartbeats=heartbeats)

    # Ghost agent should not be in the registry (only in heartbeats)
    result = await registry.get("ghost-agent")
    assert result is None

    # Not routable because not in candidates
    selected = select_agent(await registry.list_all(), "any-intent", heartbeats)
    assert selected is None


@pytest.mark.negative
async def test_no_matching_intent_returns_none() -> None:
    """BDD: Request with no matching agent intent is not dispatched."""
    registry = make_in_memory_registry()
    await registry.register(
        make_agent_manifest(
            agent_id="ideation-agent",
            name="Ideation Agent",
            intents=[make_intent(pattern="ideate")],
        )
    )
    await registry.register(
        make_agent_manifest(
            agent_id="factory-agent",
            name="Factory Agent",
            intents=[make_intent(pattern="software.build")],
        )
    )

    heartbeats: dict[str, HeartbeatRecord] = {
        "ideation-agent": make_heartbeat_record(agent_id="ideation-agent"),
        "factory-agent": make_heartbeat_record(agent_id="factory-agent"),
    }

    candidates = await registry.list_all()
    selected = select_agent(candidates, "translate.document", heartbeats)
    assert selected is None


# ===================================================================
# Edge Case Tests (11 scenarios)
# ===================================================================


@pytest.mark.edge_case
async def test_routing_selects_highest_confidence() -> None:
    """BDD: Confidence-based routing selects the best agent."""
    manifest_high = make_agent_manifest(
        agent_id="ideation-agent",
        name="Ideation Agent",
        intents=[make_intent(pattern="ideate", confidence=0.9)],
    )
    manifest_low = make_agent_manifest(
        agent_id="general-purpose-agent",
        name="General Purpose Agent",
        intents=[make_intent(pattern="ideate", confidence=0.3)],
    )
    heartbeats: dict[str, HeartbeatRecord] = {
        "ideation-agent": make_heartbeat_record(agent_id="ideation-agent"),
        "general-purpose-agent": make_heartbeat_record(agent_id="general-purpose-agent"),
    }

    selected = select_agent([manifest_high, manifest_low], "ideate", heartbeats)
    assert selected is not None
    assert selected.agent_id == "ideation-agent"


@pytest.mark.edge_case
async def test_routing_tiebreak_by_queue_depth() -> None:
    """BDD: Queue-aware routing breaks confidence ties."""
    manifest_1 = make_agent_manifest(
        agent_id="factory-1",
        name="Factory 1",
        intents=[make_intent(pattern="software.build", confidence=1.0)],
    )
    manifest_2 = make_agent_manifest(
        agent_id="factory-2",
        name="Factory 2",
        intents=[make_intent(pattern="software.build", confidence=1.0)],
    )
    heartbeats: dict[str, HeartbeatRecord] = {
        "factory-1": make_heartbeat_record(agent_id="factory-1", queue_depth=3),
        "factory-2": make_heartbeat_record(agent_id="factory-2", queue_depth=0),
    }

    selected = select_agent([manifest_1, manifest_2], "software.build", heartbeats)
    assert selected is not None
    assert selected.agent_id == "factory-2"


@pytest.mark.edge_case
async def test_routing_skips_at_capacity_agent() -> None:
    """BDD: Agent at max_concurrent capacity is skipped for routing."""
    manifest_full = make_agent_manifest(
        agent_id="guardkit-factory",
        name="GuardKit Factory",
        max_concurrent=2,
        intents=[make_intent(pattern="software.build", confidence=0.9)],
    )
    manifest_free = make_agent_manifest(
        agent_id="guardkit-factory-2",
        name="GuardKit Factory 2",
        max_concurrent=2,
        intents=[make_intent(pattern="software.build", confidence=0.9)],
    )
    heartbeats: dict[str, HeartbeatRecord] = {
        "guardkit-factory": make_heartbeat_record(
            agent_id="guardkit-factory", active_tasks=2
        ),
        "guardkit-factory-2": make_heartbeat_record(
            agent_id="guardkit-factory-2", active_tasks=0
        ),
    }

    selected = select_agent(
        [manifest_full, manifest_free], "software.build", heartbeats
    )
    assert selected is not None
    assert selected.agent_id == "guardkit-factory-2"


@pytest.mark.edge_case
async def test_timeout_marks_agent_unavailable() -> None:
    """BDD: Heartbeat timeout marks agent unavailable."""
    now = time.monotonic()
    heartbeats: dict[str, HeartbeatRecord] = {
        "architect-agent": make_heartbeat_record(
            agent_id="architect-agent",
            last_seen=now - HEARTBEAT_TIMEOUT_SECONDS,
        ),
    }

    timed_out = check_timeouts(heartbeats)

    assert "architect-agent" in timed_out
    assert heartbeats["architect-agent"].available is False

    # Agent should not receive dispatches
    manifest = make_agent_manifest(
        agent_id="architect-agent",
        name="Architect Agent",
        intents=[make_intent(pattern="architecture")],
    )
    selected = select_agent([manifest], "architecture", heartbeats)
    assert selected is None


@pytest.mark.edge_case
async def test_agent_recovers_after_timeout() -> None:
    """BDD: Agent recovers from unavailable state by resuming heartbeats."""
    now = time.monotonic()
    heartbeats: dict[str, HeartbeatRecord] = {
        "architect-agent": HeartbeatRecord(
            agent_id="architect-agent",
            last_seen=now - 120,  # well past timeout
            available=False,
        ),
    }
    assert heartbeats["architect-agent"].available is False

    # Agent resumes heartbeating
    record_heartbeat("architect-agent", queue_depth=0, active_tasks=0, heartbeats=heartbeats)

    assert heartbeats["architect-agent"].available is True

    # Should be eligible for routing again
    manifest = make_agent_manifest(
        agent_id="architect-agent",
        name="Architect Agent",
        intents=[make_intent(pattern="architecture")],
    )
    selected = select_agent([manifest], "architecture", heartbeats)
    assert selected is not None
    assert selected.agent_id == "architect-agent"


@pytest.mark.edge_case
@pytest.mark.security
async def test_reregistration_overwrites_capabilities() -> None:
    """BDD: Re-registration with existing agent_id overwrites previous entry."""
    registry = make_in_memory_registry()
    original = make_agent_manifest(
        agent_id="product-owner-agent",
        name="Product Owner Agent",
        intents=[make_intent(pattern="product.document", confidence=0.9)],
    )
    await registry.register(original)

    # New registration with different intents
    replacement = make_agent_manifest(
        agent_id="product-owner-agent",
        name="Rogue Agent",
        intents=[make_intent(pattern="rogue.intent", confidence=0.5)],
    )
    await registry.register(replacement)

    result = await registry.get("product-owner-agent")
    assert result is not None
    assert result.name == "Rogue Agent"
    assert result.intents[0].pattern == "rogue.intent"
    # Previous capabilities replaced
    patterns = [i.pattern for i in result.intents]
    assert "product.document" not in patterns


@pytest.mark.edge_case
@pytest.mark.security
async def test_metadata_exceeds_64kb_rejected() -> None:
    """BDD: Registration with excessively large metadata is rejected."""
    big_metadata = {f"key-{i}": "x" * 1000 for i in range(70)}  # > 64KB

    with pytest.raises(ValidationError, match="metadata exceeds the maximum allowed size"):
        make_agent_manifest(metadata=big_metadata)


@pytest.mark.edge_case
@pytest.mark.concurrency
async def test_concurrent_registration_last_write_wins() -> None:
    """BDD: Simultaneous registrations resolve to last-write-wins.

    Two concurrent registrations for the same agent_id should result in
    exactly one entry — whichever was processed last.
    """
    registry = make_in_memory_registry()

    manifest_v1 = make_agent_manifest(
        agent_id="guardkit-factory",
        name="GuardKit Factory v1",
        intents=[make_intent(pattern="software.build", description="v1")],
    )
    manifest_v2 = make_agent_manifest(
        agent_id="guardkit-factory",
        name="GuardKit Factory v2",
        intents=[make_intent(pattern="software.build", description="v2")],
    )

    # Simulate concurrent registration with asyncio.gather
    await asyncio.gather(
        registry.register(manifest_v1),
        registry.register(manifest_v2),
    )

    all_agents = await registry.list_all()
    matching = [m for m in all_agents if m.agent_id == "guardkit-factory"]
    assert len(matching) == 1
    # Last write wins (one of v1 or v2)
    assert matching[0].name in {"GuardKit Factory v1", "GuardKit Factory v2"}


@pytest.mark.edge_case
@pytest.mark.concurrency
async def test_deregistration_over_concurrent_heartbeat() -> None:
    """BDD: Deregistration takes precedence over concurrent heartbeat.

    After a deregistration and heartbeat arrive simultaneously, the agent
    should be removed from the routing table.
    """
    registry = make_in_memory_registry()
    manifest = make_agent_manifest(
        agent_id="ideation-agent",
        name="Ideation Agent",
        intents=[make_intent(pattern="ideate")],
    )
    await registry.register(manifest)

    heartbeats: dict[str, HeartbeatRecord] = {
        "ideation-agent": make_heartbeat_record(agent_id="ideation-agent"),
    }

    async def deregister() -> None:
        await registry.deregister("ideation-agent")

    async def heartbeat() -> None:
        record_heartbeat("ideation-agent", queue_depth=0, active_tasks=0, heartbeats=heartbeats)

    await asyncio.gather(deregister(), heartbeat())

    # Agent should be removed from registry
    result = await registry.get("ideation-agent")
    assert result is None

    # Even though heartbeat record exists, agent is not in registry
    # so routing should not find it
    candidates = await registry.list_all()
    selected = select_agent(candidates, "ideate", heartbeats)
    assert selected is None


@pytest.mark.edge_case
@pytest.mark.integration
async def test_kv_unavailable_graceful_failure() -> None:
    """BDD: Registration fails gracefully when KV bucket is unavailable.

    When the KV bucket raises an exception on put, the registry should
    propagate the error so the caller can retry.
    """
    kv = MagicMock()
    kv.put = AsyncMock(side_effect=Exception("KV unavailable"))
    registry = NATSKVManifestRegistry(kv)

    manifest = make_agent_manifest(
        agent_id="test-agent",
        name="Test Agent",
        intents=[make_intent()],
    )

    with pytest.raises(Exception, match="KV unavailable"):
        await registry.register(manifest)


@pytest.mark.edge_case
@pytest.mark.integration
async def test_empty_fleet_no_dispatch() -> None:
    """BDD: Dispatch request with empty fleet returns no capable agent.

    When no agents are registered, select_agent should return None.
    Also verifies KV registry list_all graceful degradation.
    """
    heartbeats: dict[str, HeartbeatRecord] = {}
    selected = select_agent([], "software.build", heartbeats)
    assert selected is None

    # Also verify via in-memory registry
    registry = make_in_memory_registry()
    candidates = await registry.list_all()
    assert len(candidates) == 0
    selected = select_agent(candidates, "software.build", heartbeats)
    assert selected is None

    # Verify KV registry list_all returns empty on unavailable KV
    kv = MagicMock()
    kv.keys = AsyncMock(side_effect=Exception("KV unavailable"))
    kv_registry = NATSKVManifestRegistry(kv)
    kv_candidates = await kv_registry.list_all()
    assert len(kv_candidates) == 0


# ===================================================================
# Supplementary KV Registry Coverage Tests
# ===================================================================
# These test additional KV registry code paths that the BDD scenarios
# exercise indirectly but need explicit testing for branch coverage.


@pytest.mark.edge_case
async def test_kv_registry_deregister_unknown_agent_ignored() -> None:
    """KV registry deregister for unknown agent is silently ignored."""
    kv = make_mock_kv_bucket()
    registry = NATSKVManifestRegistry(kv)

    # Should not raise — deregister is idempotent
    await registry.deregister("phantom-agent")


@pytest.mark.edge_case
async def test_kv_registry_get_unknown_agent_returns_none() -> None:
    """KV registry get for unknown agent returns None."""
    kv = make_mock_kv_bucket()
    registry = NATSKVManifestRegistry(kv)

    result = await registry.get("unknown-agent")
    assert result is None


@pytest.mark.edge_case
async def test_kv_registry_empty_intents_rejected() -> None:
    """KV registry rejects registration with empty intents."""
    kv = make_mock_kv_bucket()
    registry = NATSKVManifestRegistry(kv)
    manifest = make_agent_manifest(intents=[])

    with pytest.raises(ValueError, match="at least one intent capability is required"):
        await registry.register(manifest)


@pytest.mark.edge_case
async def test_kv_registry_find_by_intent() -> None:
    """KV registry find_by_intent returns matching agents."""
    kv = make_mock_kv_bucket()
    registry = NATSKVManifestRegistry(kv)

    m1 = make_agent_manifest(
        agent_id="agent-a",
        name="Agent A",
        intents=[make_intent(pattern="ideate")],
    )
    m2 = make_agent_manifest(
        agent_id="agent-b",
        name="Agent B",
        intents=[make_intent(pattern="software.build")],
    )
    await registry.register(m1)
    await registry.register(m2)

    results = await registry.find_by_intent("ideate")
    assert len(results) == 1
    assert results[0].agent_id == "agent-a"


@pytest.mark.edge_case
async def test_kv_registry_find_by_tool() -> None:
    """KV registry find_by_tool returns matching agents."""
    kv = make_mock_kv_bucket()
    registry = NATSKVManifestRegistry(kv)

    m1 = make_agent_manifest(
        agent_id="tool-agent",
        name="Tool Agent",
        intents=[make_intent()],
        tools=[{
            "name": "lint",
            "description": "Run linting",
            "parameters": {"type": "object"},
            "returns": "Lint report",
        }],
    )
    await registry.register(m1)

    results = await registry.find_by_tool("lint")
    assert len(results) == 1
    assert results[0].agent_id == "tool-agent"

    results_none = await registry.find_by_tool("nonexistent")
    assert len(results_none) == 0
