"""Comprehensive tests for all 13 event payload classes (TASK-NC03).

Validates:
  - AC-001: All 13 payload classes exist and instantiate with required fields
  - AC-002: All models use ConfigDict(extra="ignore")
  - AC-003: All models use from __future__ import annotations
  - AC-004: All fields have Field(description=...)
  - AC-005: BuildCompletePayload serialises to JSON matching wire format
  - AC-006: AgentHeartbeatPayload has mutable default_factory for metadata
  - AC-007: All payload classes importable from nats_core.events
  - AC-008: Lint/format compliance (verified externally)
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from nats_core.events import (
    AgentDeregistrationPayload,
    AgentHeartbeatPayload,
    AgentStatusPayload,
    ApprovalRequestPayload,
    ApprovalResponsePayload,
    BuildCompletePayload,
    BuildFailedPayload,
    BuildProgressPayload,
    BuildStartedPayload,
    DispatchPayload,
    FeaturePlannedPayload,
    FeatureReadyForBuildPayload,
    IntentClassifiedPayload,
    WaveSummary,
)

# ---------------------------------------------------------------------------
# The 13 payload classes required by AC-001 (per API-message-contracts.md)
# ---------------------------------------------------------------------------

ALL_13_PAYLOAD_CLASSES: list[type[BaseModel]] = [
    FeaturePlannedPayload,
    FeatureReadyForBuildPayload,
    BuildStartedPayload,
    BuildProgressPayload,
    BuildCompletePayload,
    BuildFailedPayload,
    AgentStatusPayload,
    ApprovalRequestPayload,
    ApprovalResponsePayload,
    IntentClassifiedPayload,
    DispatchPayload,
    AgentHeartbeatPayload,
    AgentDeregistrationPayload,
]

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def _make_wave() -> WaveSummary:
    return WaveSummary(wave_number=1, task_count=2, task_ids=["T1", "T2"])


def _make_payload(cls: type[BaseModel]) -> BaseModel:
    """Create a valid instance of any of the 13 payload classes."""
    import warnings

    factories: dict[type[BaseModel], dict[str, Any]] = {
        FeaturePlannedPayload: {
            "feature_id": "FEAT-001",
            "wave_count": 1,
            "task_count": 2,
            "waves": [_make_wave()],
        },
        FeatureReadyForBuildPayload: {
            "feature_id": "FEAT-001",
            "spec_path": "/specs/FEAT-001.yaml",
            "plan_path": "/plans/FEAT-001.md",
            "pipeline_type": "greenfield",
        },
        BuildStartedPayload: {
            "feature_id": "FEAT-001",
            "build_id": "build-FEAT-001-20260408120000",
            "wave_total": 3,
        },
        BuildProgressPayload: {
            "feature_id": "FEAT-001",
            "build_id": "build-FEAT-001-20260408120000",
            "wave": 1,
            "wave_total": 3,
            "overall_progress_pct": 33.3,
            "elapsed_seconds": 60,
        },
        BuildCompletePayload: {
            "feature_id": "FEAT-001",
            "build_id": "build-FEAT-001-20260407143000",
            "repo": "finproxy",
            "branch": "feature/FEAT-001",
            "tasks_completed": 5,
            "tasks_failed": 0,
            "tasks_total": 5,
            "pr_url": "https://github.com/appmilla/finproxy/pull/42",
            "duration_seconds": 120,
            "summary": "All 5 tasks completed successfully",
        },
        BuildFailedPayload: {
            "feature_id": "FEAT-001",
            "build_id": "build-FEAT-001-20260408120000",
            "failure_reason": "Timeout exceeded",
            "recoverable": True,
        },
        AgentStatusPayload: {
            "agent_id": "test-agent",
            "state": "running",
        },
        ApprovalRequestPayload: {
            "request_id": "REQ-001",
            "agent_id": "test-agent",
            "action_description": "Deploy to production",
            "risk_level": "high",
            "details": {"env": "production"},
        },
        ApprovalResponsePayload: {
            "request_id": "REQ-001",
            "decision": "approve",
            "decided_by": "human",
        },
        IntentClassifiedPayload: {
            "input_text": "build the login feature",
            "intent": "software.build",
            "confidence": 0.92,
            "target_agent": "product-owner-agent",
        },
        DispatchPayload: {
            "intent": "software.build",
            "target_agent": "product-owner-agent",
            "input_text": "build it",
            "correlation_id": "corr-001",
        },
        AgentHeartbeatPayload: {
            "agent_id": "test-agent",
            "status": "ready",
            "uptime_seconds": 3600,
        },
        AgentDeregistrationPayload: {
            "agent_id": "test-agent",
        },
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return cls(**factories[cls])


# ===================================================================
# AC-001: All 13 payload classes exist and instantiate with required fields
# ===================================================================


class TestAC001AllPayloadsExistAndInstantiate:
    """AC-001: All 13 payload classes exist and instantiate with required fields."""

    @pytest.mark.smoke
    def test_exactly_13_payload_classes(self) -> None:
        """There are exactly 13 payload classes as specified by the contract."""
        assert len(ALL_13_PAYLOAD_CLASSES) == 13  # noqa: PLR2004

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "cls",
        ALL_13_PAYLOAD_CLASSES,
        ids=[c.__name__ for c in ALL_13_PAYLOAD_CLASSES],
    )
    def test_payload_class_instantiates(self, cls: type[BaseModel]) -> None:
        """Each payload class instantiates with its required fields."""
        instance = _make_payload(cls)
        assert isinstance(instance, cls)
        assert isinstance(instance, BaseModel)

    @pytest.mark.smoke
    def test_feature_planned_has_expected_fields(self) -> None:
        p = _make_payload(FeaturePlannedPayload)
        assert isinstance(p, FeaturePlannedPayload)
        assert p.feature_id == "FEAT-001"  # type: ignore[union-attr]
        assert p.wave_count == 1  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_feature_ready_for_build_has_expected_fields(self) -> None:
        p = _make_payload(FeatureReadyForBuildPayload)
        assert isinstance(p, FeatureReadyForBuildPayload)
        assert p.feature_id == "FEAT-001"  # type: ignore[union-attr]
        assert p.pipeline_type == "greenfield"  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_build_started_has_expected_fields(self) -> None:
        p = _make_payload(BuildStartedPayload)
        assert isinstance(p, BuildStartedPayload)
        assert p.feature_id == "FEAT-001"  # type: ignore[union-attr]
        assert p.wave_total == 3  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_build_progress_has_expected_fields(self) -> None:
        p = _make_payload(BuildProgressPayload)
        assert isinstance(p, BuildProgressPayload)
        assert p.wave == 1  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_build_complete_has_expected_fields(self) -> None:
        p = _make_payload(BuildCompletePayload)
        assert isinstance(p, BuildCompletePayload)
        assert p.tasks_total == 5  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_build_failed_has_expected_fields(self) -> None:
        p = _make_payload(BuildFailedPayload)
        assert isinstance(p, BuildFailedPayload)
        assert p.failure_reason == "Timeout exceeded"  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_agent_status_has_expected_fields(self) -> None:
        p = _make_payload(AgentStatusPayload)
        assert isinstance(p, AgentStatusPayload)
        assert p.state == "running"  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_approval_request_has_expected_fields(self) -> None:
        p = _make_payload(ApprovalRequestPayload)
        assert isinstance(p, ApprovalRequestPayload)
        assert p.risk_level == "high"  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_approval_response_has_expected_fields(self) -> None:
        p = _make_payload(ApprovalResponsePayload)
        assert isinstance(p, ApprovalResponsePayload)
        assert p.decision == "approve"  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_intent_classified_has_expected_fields(self) -> None:
        p = _make_payload(IntentClassifiedPayload)
        assert isinstance(p, IntentClassifiedPayload)
        assert p.confidence == pytest.approx(0.92)  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_dispatch_has_expected_fields(self) -> None:
        p = _make_payload(DispatchPayload)
        assert isinstance(p, DispatchPayload)
        assert p.target_agent == "product-owner-agent"  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_heartbeat_has_expected_fields(self) -> None:
        p = _make_payload(AgentHeartbeatPayload)
        assert isinstance(p, AgentHeartbeatPayload)
        assert p.uptime_seconds == 3600  # type: ignore[union-attr]

    @pytest.mark.smoke
    def test_deregistration_has_expected_fields(self) -> None:
        p = _make_payload(AgentDeregistrationPayload)
        assert isinstance(p, AgentDeregistrationPayload)
        assert p.agent_id == "test-agent"  # type: ignore[union-attr]


# ===================================================================
# AC-002: All models use ConfigDict(extra="ignore")
# ===================================================================


class TestAC002ConfigDictExtraIgnore:
    """AC-002: All models use ConfigDict(extra='ignore')."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "cls",
        ALL_13_PAYLOAD_CLASSES,
        ids=[c.__name__ for c in ALL_13_PAYLOAD_CLASSES],
    )
    def test_model_config_extra_ignore(self, cls: type[BaseModel]) -> None:
        """Model config has extra='ignore'."""
        config = cls.model_config
        assert config.get("extra") == "ignore", (
            f"{cls.__name__} does not have extra='ignore' in model_config"
        )

    @pytest.mark.edge_case
    @pytest.mark.parametrize(
        "cls",
        ALL_13_PAYLOAD_CLASSES,
        ids=[c.__name__ for c in ALL_13_PAYLOAD_CLASSES],
    )
    def test_extra_fields_silently_discarded(self, cls: type[BaseModel]) -> None:
        """Extra fields are silently discarded (not stored)."""
        instance = _make_payload(cls)
        data = instance.model_dump()
        data["unknown_future_field"] = "should be ignored"
        restored = cls(**data)
        assert not hasattr(restored, "unknown_future_field")


# ===================================================================
# AC-003: All models use from __future__ import annotations
# ===================================================================


class TestAC003FutureAnnotations:
    """AC-003: All event modules use from __future__ import annotations."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "module_name",
        [
            "nats_core.events._pipeline",
            "nats_core.events._agent",
            "nats_core.events._jarvis",
            "nats_core.events._fleet",
            "nats_core.events",
        ],
    )
    def test_module_has_future_annotations(self, module_name: str) -> None:
        """Module source starts with from __future__ import annotations."""
        import importlib

        mod = importlib.import_module(module_name)
        source_file = inspect.getfile(mod)
        source = Path(source_file).read_text()
        tree = ast.parse(source)
        # Check that the first non-docstring import is from __future__
        has_future = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(alias.name == "annotations" for alias in node.names)
            for node in ast.walk(tree)
        )
        assert has_future, f"{module_name} missing 'from __future__ import annotations'"


# ===================================================================
# AC-004: All fields have Field(description=...)
# ===================================================================


class TestAC004FieldDescriptions:
    """AC-004: All fields have Field(description=...)."""

    @pytest.mark.smoke
    @pytest.mark.parametrize(
        "cls",
        ALL_13_PAYLOAD_CLASSES,
        ids=[c.__name__ for c in ALL_13_PAYLOAD_CLASSES],
    )
    def test_all_fields_have_descriptions(self, cls: type[BaseModel]) -> None:
        """Every field in the model has a non-empty description."""
        for field_name, field_info in cls.model_fields.items():
            assert field_info.description is not None, (
                f"{cls.__name__}.{field_name} has no description"
            )
            assert len(field_info.description) > 0, (
                f"{cls.__name__}.{field_name} has empty description"
            )


# ===================================================================
# AC-005: BuildCompletePayload serialises to JSON matching wire format
# ===================================================================


class TestAC005BuildCompleteWireFormat:
    """AC-005: BuildCompletePayload serialises to JSON matching wire format."""

    @pytest.mark.smoke
    def test_build_complete_matches_wire_format_keys(self) -> None:
        """BuildCompletePayload JSON output contains all wire format keys."""
        payload = BuildCompletePayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260407143000",
            repo="finproxy",
            branch="feature/FEAT-001",
            pr_url="https://github.com/appmilla/finproxy/pull/42",
            duration_seconds=120,
            tasks_completed=5,
            tasks_failed=0,
            tasks_total=5,
            summary="All 5 tasks completed successfully",
        )
        wire_json = json.loads(payload.model_dump_json())

        # The wire format payload fields from API-message-contracts.md
        expected_keys = {
            "feature_id",
            "build_id",
            "repo",
            "branch",
            "pr_url",
            "duration_seconds",
            "tasks_completed",
            "tasks_failed",
            "tasks_total",
            "summary",
        }
        assert expected_keys.issubset(set(wire_json.keys()))

    @pytest.mark.smoke
    def test_build_complete_wire_format_values(self) -> None:
        """BuildCompletePayload JSON values match the documented wire format."""
        payload = BuildCompletePayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260407143000",
            repo="finproxy",
            branch="feature/FEAT-001",
            pr_url="https://github.com/appmilla/finproxy/pull/42",
            duration_seconds=120,
            tasks_completed=5,
            tasks_failed=0,
            tasks_total=5,
            summary="All 5 tasks completed successfully",
        )
        wire = json.loads(payload.model_dump_json())

        assert wire["feature_id"] == "FEAT-001"
        assert wire["build_id"] == "build-FEAT-001-20260407143000"
        assert wire["repo"] == "finproxy"
        assert wire["branch"] == "feature/FEAT-001"
        assert wire["pr_url"] == "https://github.com/appmilla/finproxy/pull/42"
        assert wire["duration_seconds"] == 120  # noqa: PLR2004
        assert wire["tasks_completed"] == 5  # noqa: PLR2004
        assert wire["tasks_failed"] == 0
        assert wire["tasks_total"] == 5  # noqa: PLR2004
        assert wire["summary"] == "All 5 tasks completed successfully"

    @pytest.mark.smoke
    def test_build_complete_repo_and_branch_optional(self) -> None:
        """repo and branch fields default to None when not provided."""
        payload = BuildCompletePayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260407143000",
            tasks_completed=5,
            tasks_failed=0,
            tasks_total=5,
            duration_seconds=120,
            summary="Done",
        )
        assert payload.repo is None
        assert payload.branch is None

    @pytest.mark.edge_case
    def test_build_complete_round_trip_with_wire_format_data(self) -> None:
        """Parse wire-format JSON into BuildCompletePayload and back."""
        wire_payload = {
            "feature_id": "FEAT-001",
            "build_id": "build-FEAT-001-20260407143000",
            "repo": "finproxy",
            "branch": "feature/FEAT-001",
            "pr_url": "https://github.com/appmilla/finproxy/pull/42",
            "duration_seconds": 120,
            "tasks_completed": 5,
            "tasks_failed": 0,
            "tasks_total": 5,
            "summary": "All 5 tasks completed successfully",
        }
        parsed = BuildCompletePayload.model_validate(wire_payload)
        reserialized = json.loads(parsed.model_dump_json())

        # All keys from the wire format are present in the reserialized output
        for key in wire_payload:
            assert key in reserialized, f"Missing key: {key}"
            assert reserialized[key] == wire_payload[key], (
                f"Value mismatch for {key}: {reserialized[key]} != {wire_payload[key]}"
            )


# ===================================================================
# AC-006: AgentHeartbeatPayload has mutable default_factory for metadata
# ===================================================================


class TestAC006HeartbeatMetadataDefaultFactory:
    """AC-006: AgentHeartbeatPayload.metadata uses default_factory, not {}."""

    @pytest.mark.smoke
    def test_heartbeat_has_metadata_field(self) -> None:
        """AgentHeartbeatPayload has a metadata field."""
        assert "metadata" in AgentHeartbeatPayload.model_fields

    @pytest.mark.smoke
    def test_metadata_defaults_to_empty_dict(self) -> None:
        """metadata defaults to empty dict (not required)."""
        hb = AgentHeartbeatPayload(
            agent_id="test-agent",
            status="ready",
            uptime_seconds=100,
        )
        assert hb.metadata == {}

    @pytest.mark.smoke
    def test_metadata_uses_default_factory_not_mutable_default(self) -> None:
        """Each instance gets a new dict, confirming default_factory is used."""
        hb1 = AgentHeartbeatPayload(
            agent_id="agent-a",
            status="ready",
            uptime_seconds=100,
        )
        hb2 = AgentHeartbeatPayload(
            agent_id="agent-b",
            status="busy",
            uptime_seconds=200,
        )
        # Both start empty but are distinct objects
        assert hb1.metadata == {}
        assert hb2.metadata == {}
        assert hb1.metadata is not hb2.metadata

    @pytest.mark.smoke
    def test_metadata_field_has_default_factory(self) -> None:
        """The metadata field info uses default_factory (not a plain default)."""
        field_info = AgentHeartbeatPayload.model_fields["metadata"]
        assert field_info.default_factory is not None, (
            "metadata should use default_factory, not a plain default"
        )

    @pytest.mark.edge_case
    def test_metadata_accepts_arbitrary_data(self) -> None:
        """metadata dict can hold arbitrary key-value pairs."""
        hb = AgentHeartbeatPayload(
            agent_id="test-agent",
            status="ready",
            uptime_seconds=100,
            metadata={"region": "us-east", "version": "1.2.3"},
        )
        assert hb.metadata == {"region": "us-east", "version": "1.2.3"}

    @pytest.mark.edge_case
    def test_metadata_mutation_does_not_affect_other_instances(self) -> None:
        """Mutating one instance's metadata does not affect another."""
        hb1 = AgentHeartbeatPayload(agent_id="agent-a", status="ready", uptime_seconds=100)
        hb2 = AgentHeartbeatPayload(agent_id="agent-b", status="ready", uptime_seconds=200)
        hb1.metadata["key"] = "value"
        assert "key" not in hb2.metadata


# ===================================================================
# AC-007: All payload classes importable from nats_core.events
# ===================================================================


class TestAC007ImportsFromNatsCoreEvents:
    """AC-007: All payload classes importable from nats_core.events."""

    @pytest.mark.smoke
    def test_all_13_importable_from_events(self) -> None:
        """All 13 payload classes can be imported from nats_core.events."""
        import nats_core.events as events_mod

        expected_names = {
            "FeaturePlannedPayload",
            "FeatureReadyForBuildPayload",
            "BuildStartedPayload",
            "BuildProgressPayload",
            "BuildCompletePayload",
            "BuildFailedPayload",
            "AgentStatusPayload",
            "ApprovalRequestPayload",
            "ApprovalResponsePayload",
            "IntentClassifiedPayload",
            "DispatchPayload",
            "AgentHeartbeatPayload",
            "AgentDeregistrationPayload",
        }
        for name in expected_names:
            assert hasattr(events_mod, name), f"{name} not importable from nats_core.events"

    @pytest.mark.smoke
    def test_all_13_in_dunder_all(self) -> None:
        """All 13 payload classes are listed in nats_core.events.__all__."""
        import nats_core.events as events_mod

        expected_names = {
            "FeaturePlannedPayload",
            "FeatureReadyForBuildPayload",
            "BuildStartedPayload",
            "BuildProgressPayload",
            "BuildCompletePayload",
            "BuildFailedPayload",
            "AgentStatusPayload",
            "ApprovalRequestPayload",
            "ApprovalResponsePayload",
            "IntentClassifiedPayload",
            "DispatchPayload",
            "AgentHeartbeatPayload",
            "AgentDeregistrationPayload",
        }
        assert expected_names.issubset(set(events_mod.__all__)), (
            f"Missing from __all__: {expected_names - set(events_mod.__all__)}"
        )


# ===================================================================
# JSON round-trip tests for all 13 classes
# ===================================================================


class TestJsonRoundTrip:
    """JSON round-trip fidelity for all 13 payload classes."""

    @pytest.mark.edge_case
    @pytest.mark.parametrize(
        "cls",
        ALL_13_PAYLOAD_CLASSES,
        ids=[c.__name__ for c in ALL_13_PAYLOAD_CLASSES],
    )
    def test_json_round_trip(self, cls: type[BaseModel]) -> None:
        """Each payload class survives a JSON round-trip with fidelity."""
        instance = _make_payload(cls)
        dumped = instance.model_dump(mode="json")
        restored = cls.model_validate(dumped)
        assert restored == instance, f"Round-trip failed for {cls.__name__}"
