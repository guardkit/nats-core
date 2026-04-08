"""Tests for event payload models — mutable defaults, isolation, and field validation.

Covers TASK-NC08 acceptance criteria:
  - AC-003: AgentHeartbeatPayload.metadata mutable default isolation
  - General event payload validation and default_factory correctness

Uses factory functions (no ``pytest.fixture`` with mutable state).
"""

from __future__ import annotations

from typing import Any

import pytest

from nats_core.events._fleet import AgentDeregistrationPayload, AgentHeartbeatPayload

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _make_heartbeat(**overrides: Any) -> AgentHeartbeatPayload:
    """Create an AgentHeartbeatPayload with sensible defaults and optional overrides."""
    defaults: dict[str, Any] = {
        "agent_id": "test-agent",
        "status": "ready",
        "uptime_seconds": 100,
    }
    defaults.update(overrides)
    return AgentHeartbeatPayload(**defaults)


# ===========================================================================
# AC-003: AgentHeartbeatPayload.metadata mutable default isolation
# ===========================================================================


class TestHeartbeatMetadataMutableDefaultIsolation:
    """Verify metadata uses default_factory=dict, not a shared mutable default."""

    @pytest.mark.smoke
    def test_metadata_defaults_to_empty_dict(self) -> None:
        """metadata defaults to an empty dict when not provided."""
        hb = _make_heartbeat()
        assert hb.metadata == {}

    @pytest.mark.smoke
    def test_two_instances_have_distinct_metadata_objects(self) -> None:
        """Two instances created without explicit metadata get distinct dicts."""
        hb1 = _make_heartbeat(agent_id="agent-a")
        hb2 = _make_heartbeat(agent_id="agent-b")
        assert hb1.metadata is not hb2.metadata

    @pytest.mark.smoke
    def test_mutating_one_does_not_affect_other(self) -> None:
        """Mutating metadata on instance A does not affect instance B."""
        hb1 = _make_heartbeat(agent_id="agent-a")
        hb2 = _make_heartbeat(agent_id="agent-b")

        hb1.metadata["key"] = "only-on-a"

        assert "key" in hb1.metadata
        assert "key" not in hb2.metadata, (
            "Mutable default leaked: mutating hb1.metadata affected hb2"
        )

    @pytest.mark.smoke
    def test_metadata_field_uses_default_factory(self) -> None:
        """The metadata FieldInfo uses default_factory, not a plain default."""
        field_info = AgentHeartbeatPayload.model_fields["metadata"]
        assert field_info.default_factory is not None, (
            "metadata must use default_factory=dict to avoid mutable default sharing"
        )

    @pytest.mark.edge_case
    def test_metadata_accepts_arbitrary_values(self) -> None:
        """metadata dict accepts arbitrary key-value pairs."""
        hb = _make_heartbeat(metadata={"region": "eu-west", "tags": ["a", "b"]})
        assert hb.metadata["region"] == "eu-west"
        assert hb.metadata["tags"] == ["a", "b"]

    @pytest.mark.edge_case
    def test_many_instances_all_independent(self) -> None:
        """Creating many instances and mutating each one keeps all independent."""
        instances = [_make_heartbeat(agent_id=f"agent-{i}") for i in range(10)]
        for i, inst in enumerate(instances):
            inst.metadata[f"key-{i}"] = f"val-{i}"

        for i, inst in enumerate(instances):
            assert inst.metadata == {f"key-{i}": f"val-{i}"}, (
                f"Instance {i} has unexpected metadata: {inst.metadata}"
            )


# ===========================================================================
# AgentHeartbeatPayload active_workflow_states mutable default isolation
# ===========================================================================


class TestHeartbeatWorkflowStatesMutableDefault:
    """Verify active_workflow_states uses default_factory=dict."""

    @pytest.mark.smoke
    def test_active_workflow_states_defaults_to_empty_dict(self) -> None:
        hb = _make_heartbeat()
        assert hb.active_workflow_states == {}

    @pytest.mark.smoke
    def test_two_instances_have_distinct_workflow_states(self) -> None:
        hb1 = _make_heartbeat(agent_id="agent-a")
        hb2 = _make_heartbeat(agent_id="agent-b")
        assert hb1.active_workflow_states is not hb2.active_workflow_states

    @pytest.mark.smoke
    def test_workflow_states_mutation_isolation(self) -> None:
        hb1 = _make_heartbeat(agent_id="agent-a")
        hb2 = _make_heartbeat(agent_id="agent-b")
        hb1.active_workflow_states["wf-1"] = "running"
        assert "wf-1" not in hb2.active_workflow_states

    @pytest.mark.smoke
    def test_workflow_states_field_uses_default_factory(self) -> None:
        field_info = AgentHeartbeatPayload.model_fields["active_workflow_states"]
        assert field_info.default_factory is not None


# ===========================================================================
# AgentDeregistrationPayload basic validation
# ===========================================================================


class TestAgentDeregistrationPayload:
    """Basic validation for AgentDeregistrationPayload."""

    @pytest.mark.smoke
    def test_valid_deregistration(self) -> None:
        dereg = AgentDeregistrationPayload(agent_id="my-agent")
        assert dereg.agent_id == "my-agent"
        assert dereg.reason == "shutdown"

    @pytest.mark.negative
    def test_invalid_agent_id_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AgentDeregistrationPayload(agent_id="INVALID-ID")

    @pytest.mark.edge_case
    def test_extra_fields_ignored(self) -> None:
        dereg = AgentDeregistrationPayload(
            agent_id="my-agent",
            unknown="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(dereg, "unknown")
