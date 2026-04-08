"""Tests for fleet event payloads and agent manifest (TASK-ETS4).

Covers AgentHeartbeatPayload, AgentDeregistrationPayload, and
AgentManifest with its nested IntentCapability and ToolCapability models.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from nats_core.events._fleet import AgentDeregistrationPayload, AgentHeartbeatPayload
from nats_core.manifest import AgentManifest, IntentCapability, ToolCapability


# ---------------------------------------------------------------------------
# IntentCapability
# ---------------------------------------------------------------------------


class TestIntentCapability:
    """Tests for IntentCapability model."""

    @pytest.mark.smoke
    def test_valid_intent_capability(self) -> None:
        cap = IntentCapability(
            pattern="schedule.*",
            description="Scheduling intent",
        )
        assert cap.pattern == "schedule.*"
        assert cap.signals == []
        assert cap.confidence == 1.0 or cap.confidence >= 0.0  # default is valid
        assert cap.description == "Scheduling intent"

    @pytest.mark.key_example
    def test_intent_capability_with_all_fields(self) -> None:
        cap = IntentCapability(
            pattern="deploy.*",
            signals=["urgent", "production"],
            confidence=0.85,
            description="Deployment intent",
        )
        assert cap.pattern == "deploy.*"
        assert cap.signals == ["urgent", "production"]
        assert cap.confidence == 0.85
        assert cap.description == "Deployment intent"

    @pytest.mark.negative
    def test_intent_capability_empty_pattern_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IntentCapability(pattern="", description="Empty pattern")

    @pytest.mark.boundary
    def test_intent_capability_confidence_bounds(self) -> None:
        # Valid at boundaries
        cap_zero = IntentCapability(pattern="x", confidence=0.0, description="zero")
        assert cap_zero.confidence == 0.0
        cap_one = IntentCapability(pattern="x", confidence=1.0, description="one")
        assert cap_one.confidence == 1.0

        # Invalid beyond boundaries
        with pytest.raises(ValidationError):
            IntentCapability(pattern="x", confidence=-0.1, description="negative")
        with pytest.raises(ValidationError):
            IntentCapability(pattern="x", confidence=1.1, description="over one")


# ---------------------------------------------------------------------------
# ToolCapability
# ---------------------------------------------------------------------------


class TestToolCapability:
    """Tests for ToolCapability model."""

    @pytest.mark.smoke
    def test_valid_tool_capability(self) -> None:
        tool = ToolCapability(
            name="run-tests",
            description="Run test suite",
            parameters={"type": "object", "properties": {}},
            returns="TestResult",
        )
        assert tool.name == "run-tests"
        assert tool.risk_level == "read_only"
        assert tool.async_mode is False
        assert tool.requires_approval is False

    @pytest.mark.key_example
    def test_tool_capability_with_all_fields(self) -> None:
        tool = ToolCapability(
            name="delete-resource",
            description="Delete a resource",
            parameters={"type": "object"},
            returns="DeletionResult",
            risk_level="destructive",
            async_mode=True,
            requires_approval=True,
        )
        assert tool.risk_level == "destructive"
        assert tool.async_mode is True
        assert tool.requires_approval is True

    @pytest.mark.negative
    def test_tool_capability_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ToolCapability(
                name="",
                description="Empty name",
                parameters={},
                returns="str",
            )


# ---------------------------------------------------------------------------
# AgentManifest
# ---------------------------------------------------------------------------


class TestAgentManifest:
    """Tests for AgentManifest model."""

    @pytest.mark.smoke
    def test_valid_agent_manifest_minimal(self) -> None:
        manifest = AgentManifest(
            agent_id="my-agent",
            name="My Agent",
            template="worker",
        )
        assert manifest.agent_id == "my-agent"
        assert manifest.name == "My Agent"
        assert manifest.version == "0.1.0"
        assert manifest.intents == []
        assert manifest.tools == []
        assert manifest.template == "worker"
        assert manifest.max_concurrent == 1
        assert manifest.status == "ready"
        assert manifest.trust_tier == "specialist"
        assert manifest.required_permissions == []
        assert manifest.container_id is None
        assert manifest.metadata == {}

    @pytest.mark.key_example
    def test_agent_manifest_full(self) -> None:
        manifest = AgentManifest(
            agent_id="code-builder",
            name="Code Builder",
            version="1.2.0",
            intents=[
                IntentCapability(
                    pattern="build.*",
                    signals=["compile"],
                    confidence=0.9,
                    description="Build intent",
                )
            ],
            tools=[
                ToolCapability(
                    name="compile",
                    description="Compile code",
                    parameters={"type": "object"},
                    returns="BuildResult",
                )
            ],
            template="builder",
            max_concurrent=4,
            status="starting",
            trust_tier="core",
            required_permissions=["write:code"],
            container_id="abc123",
            metadata={"region": "us-east"},
        )
        assert manifest.version == "1.2.0"
        assert len(manifest.intents) == 1
        assert len(manifest.tools) == 1
        assert manifest.max_concurrent == 4
        assert manifest.status == "starting"
        assert manifest.trust_tier == "core"
        assert manifest.container_id == "abc123"

    @pytest.mark.negative
    def test_agent_manifest_invalid_agent_id_uppercase(self) -> None:
        with pytest.raises(ValidationError):
            AgentManifest(agent_id="MyAgent", name="A", template="t")

    @pytest.mark.negative
    def test_agent_manifest_invalid_agent_id_spaces(self) -> None:
        with pytest.raises(ValidationError):
            AgentManifest(agent_id="my agent", name="A", template="t")

    @pytest.mark.negative
    def test_agent_manifest_invalid_agent_id_starts_with_number(self) -> None:
        with pytest.raises(ValidationError):
            AgentManifest(agent_id="1agent", name="A", template="t")

    @pytest.mark.boundary
    def test_agent_manifest_max_concurrent_must_be_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            AgentManifest(
                agent_id="a", name="A", template="t", max_concurrent=0
            )

    @pytest.mark.edge_case
    def test_agent_manifest_extra_fields_ignored(self) -> None:
        manifest = AgentManifest(
            agent_id="my-agent",
            name="My Agent",
            template="worker",
            unknown_field="should be ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(manifest, "unknown_field")

    @pytest.mark.boundary
    def test_agent_manifest_valid_kebab_case_ids(self) -> None:
        for valid_id in ["a", "agent", "my-agent", "a1", "agent-v2-beta"]:
            manifest = AgentManifest(
                agent_id=valid_id, name="N", template="t"
            )
            assert manifest.agent_id == valid_id


# ---------------------------------------------------------------------------
# AgentHeartbeatPayload
# ---------------------------------------------------------------------------


class TestAgentHeartbeatPayload:
    """Tests for AgentHeartbeatPayload model."""

    @pytest.mark.smoke
    def test_valid_heartbeat_minimal(self) -> None:
        hb = AgentHeartbeatPayload(
            agent_id="worker-1",
            status="ready",
            uptime_seconds=120,
        )
        assert hb.agent_id == "worker-1"
        assert hb.status == "ready"
        assert hb.queue_depth == 0
        assert hb.active_tasks == 0
        assert hb.uptime_seconds == 120
        assert hb.last_task_completed_at is None
        assert hb.active_workflow_states == {}

    @pytest.mark.key_example
    def test_valid_heartbeat_full(self) -> None:
        now = datetime.now(timezone.utc)
        hb = AgentHeartbeatPayload(
            agent_id="worker-1",
            status="busy",
            queue_depth=5,
            active_tasks=2,
            uptime_seconds=3600,
            last_task_completed_at=now,
            active_workflow_states={"wf-1": "running", "wf-2": "paused"},
        )
        assert hb.queue_depth == 5
        assert hb.active_tasks == 2
        assert hb.last_task_completed_at == now
        assert hb.active_workflow_states == {"wf-1": "running", "wf-2": "paused"}

    @pytest.mark.boundary
    def test_heartbeat_queue_depth_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            AgentHeartbeatPayload(
                agent_id="a", status="ready", uptime_seconds=0, queue_depth=-1
            )

    @pytest.mark.boundary
    def test_heartbeat_active_tasks_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            AgentHeartbeatPayload(
                agent_id="a", status="ready", uptime_seconds=0, active_tasks=-1
            )

    @pytest.mark.boundary
    def test_heartbeat_uptime_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            AgentHeartbeatPayload(
                agent_id="a", status="ready", uptime_seconds=-1
            )

    @pytest.mark.negative
    def test_heartbeat_invalid_status(self) -> None:
        with pytest.raises(ValidationError):
            AgentHeartbeatPayload(
                agent_id="a", status="unknown", uptime_seconds=0  # type: ignore[arg-type]
            )

    @pytest.mark.edge_case
    def test_heartbeat_extra_fields_ignored(self) -> None:
        hb = AgentHeartbeatPayload(
            agent_id="a",
            status="ready",
            uptime_seconds=0,
            extra_field="ignored",  # type: ignore[call-arg]
        )
        assert not hasattr(hb, "extra_field")


# ---------------------------------------------------------------------------
# AgentDeregistrationPayload
# ---------------------------------------------------------------------------


class TestAgentDeregistrationPayload:
    """Tests for AgentDeregistrationPayload model."""

    @pytest.mark.smoke
    def test_valid_deregistration_default_reason(self) -> None:
        dereg = AgentDeregistrationPayload(agent_id="my-agent")
        assert dereg.agent_id == "my-agent"
        assert dereg.reason == "shutdown"

    @pytest.mark.key_example
    def test_valid_deregistration_custom_reason(self) -> None:
        dereg = AgentDeregistrationPayload(
            agent_id="my-agent", reason="maintenance"
        )
        assert dereg.reason == "maintenance"

    @pytest.mark.negative
    def test_deregistration_invalid_agent_id(self) -> None:
        with pytest.raises(ValidationError):
            AgentDeregistrationPayload(agent_id="Invalid-ID")

    @pytest.mark.negative
    def test_deregistration_agent_id_starts_with_number(self) -> None:
        with pytest.raises(ValidationError):
            AgentDeregistrationPayload(agent_id="1agent")

    @pytest.mark.edge_case
    def test_deregistration_extra_fields_ignored(self) -> None:
        dereg = AgentDeregistrationPayload(
            agent_id="my-agent", extra="ignored"  # type: ignore[call-arg]
        )
        assert not hasattr(dereg, "extra")


# ---------------------------------------------------------------------------
# Export checks
# ---------------------------------------------------------------------------


class TestExports:
    """Tests that all models are properly exported from their packages."""

    @pytest.mark.smoke
    def test_fleet_payloads_exported_from_events(self) -> None:
        from nats_core.events import AgentDeregistrationPayload as ADP
        from nats_core.events import AgentHeartbeatPayload as AHP

        assert AHP is AgentHeartbeatPayload
        assert ADP is AgentDeregistrationPayload

    @pytest.mark.smoke
    def test_manifest_models_exported_from_nats_core(self) -> None:
        from nats_core import AgentManifest as AM
        from nats_core import IntentCapability as IC
        from nats_core import ToolCapability as TC

        assert AM is AgentManifest
        assert IC is IntentCapability
        assert TC is ToolCapability
