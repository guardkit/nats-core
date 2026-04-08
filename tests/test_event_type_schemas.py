"""Full test suite for event-type-schemas: dispatcher + all 46 BDD scenarios.

Covers smoke, boundary, negative, edge-case, and seam tests for the
payload_class_for_event_type dispatcher and all 18 payload models.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from nats_core.envelope import EventType, payload_class_for_event_type
from nats_core.events import (
    AgentDeregistrationPayload,
    AgentHeartbeatPayload,
    AgentResultPayload,
    AgentStatusPayload,
    ApprovalRequestPayload,
    ApprovalResponsePayload,
    BuildCompletePayload,
    BuildFailedPayload,
    BuildProgressPayload,
    BuildStartedPayload,
    CommandPayload,
    DispatchPayload,
    FeaturePlannedPayload,
    FeatureReadyForBuildPayload,
    IntentClassifiedPayload,
    NotificationPayload,
    ResultPayload,
    WaveSummary,
)
from nats_core.manifest import AgentManifest, IntentCapability

# ---------------------------------------------------------------------------
# Factory helpers (conftest-style, in-module for self-contained test file)
# ---------------------------------------------------------------------------


def _make_wave_summary(**overrides: Any) -> WaveSummary:
    defaults: dict[str, Any] = {
        "wave_number": 1,
        "task_count": 2,
        "task_ids": ["TASK-001", "TASK-002"],
    }
    defaults.update(overrides)
    return WaveSummary(**defaults)


def _make_feature_planned(**overrides: Any) -> FeaturePlannedPayload:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-001",
        "wave_count": 1,
        "task_count": 2,
        "waves": [_make_wave_summary()],
    }
    defaults.update(overrides)
    return FeaturePlannedPayload(**defaults)


def _make_build_progress(**overrides: Any) -> BuildProgressPayload:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-001",
        "build_id": "build-FEAT-001-20260408120000",
        "wave": 1,
        "wave_total": 3,
        "overall_progress_pct": 33.3,
        "elapsed_seconds": 60,
    }
    defaults.update(overrides)
    return BuildProgressPayload(**defaults)


def _make_build_complete(**overrides: Any) -> BuildCompletePayload:
    defaults: dict[str, Any] = {
        "feature_id": "FEAT-001",
        "build_id": "build-FEAT-001-20260408120000",
        "tasks_completed": 5,
        "tasks_failed": 0,
        "tasks_total": 5,
        "duration_seconds": 120,
        "summary": "All tasks completed successfully",
    }
    defaults.update(overrides)
    return BuildCompletePayload(**defaults)


def _make_approval_request(**overrides: Any) -> ApprovalRequestPayload:
    defaults: dict[str, Any] = {
        "request_id": "REQ-001",
        "agent_id": "test-agent",
        "action_description": "Deploy to production",
        "risk_level": "high",
        "details": {"env": "production"},
    }
    defaults.update(overrides)
    return ApprovalRequestPayload(**defaults)


def _make_intent_classified(**overrides: Any) -> IntentClassifiedPayload:
    defaults: dict[str, Any] = {
        "input_text": "build the login feature",
        "intent": "software.build",
        "confidence": 0.92,
        "target_agent": "product-owner-agent",
    }
    defaults.update(overrides)
    return IntentClassifiedPayload(**defaults)


def _make_agent_manifest(**overrides: Any) -> AgentManifest:
    defaults: dict[str, Any] = {
        "agent_id": "product-owner-agent",
        "name": "Product Owner Agent",
        "template": "product-owner",
        "intents": [
            IntentCapability(
                pattern="software.*",
                description="Handles software intents",
            )
        ],
    }
    defaults.update(overrides)
    return AgentManifest(**defaults)


def _make_dispatch(**overrides: Any) -> DispatchPayload:
    defaults: dict[str, Any] = {
        "intent": "software.build",
        "target_agent": "product-owner-agent",
        "input_text": "build it",
        "correlation_id": "corr-001",
    }
    defaults.update(overrides)
    return DispatchPayload(**defaults)


def _make_agent_heartbeat(**overrides: Any) -> AgentHeartbeatPayload:
    defaults: dict[str, Any] = {
        "agent_id": "test-agent",
        "status": "ready",
        "uptime_seconds": 3600,
    }
    defaults.update(overrides)
    return AgentHeartbeatPayload(**defaults)


def _make_agent_status(**overrides: Any) -> AgentStatusPayload:
    defaults: dict[str, Any] = {
        "agent_id": "test-agent",
        "state": "running",
    }
    defaults.update(overrides)
    return AgentStatusPayload(**defaults)


# ===================================================================
# SMOKE TESTS (10 @smoke)
# ===================================================================


class TestSmoke:
    """Key example scenarios — core happy-path tests."""

    @pytest.mark.smoke
    def test_event_type_enum_contains_all_19_members(self) -> None:
        """EventType enum contains all 19 documented event type strings.

        Pipeline(6) + Agent(6) + Jarvis(4) + Fleet(3) = 19.
        """
        expected = {
            "feature_planned",
            "feature_ready_for_build",
            "build_started",
            "build_progress",
            "build_complete",
            "build_failed",
            "status",
            "approval_request",
            "approval_response",
            "command",
            "result",
            "error",
            "intent_classified",
            "dispatch",
            "agent_result",
            "notification",
            "agent_register",
            "agent_heartbeat",
            "agent_deregister",
        }
        actual = {member.value for member in EventType}
        assert actual == expected
        assert len(EventType) == 19  # noqa: PLR2004

    @pytest.mark.smoke
    def test_every_event_type_has_registered_payload_class(self) -> None:
        """Every EventType member has a registered payload class."""
        for et in EventType:
            cls = payload_class_for_event_type(et)
            assert cls is not None, f"No payload class registered for {et}"
            assert issubclass(cls, BaseModel), f"{et}: not a Pydantic BaseModel"

    @pytest.mark.smoke
    def test_build_started_value_equals_build_started(self) -> None:
        """EventType.BUILD_STARTED value equals 'build_started' (str enum)."""
        assert EventType.BUILD_STARTED.value == "build_started"
        assert EventType.BUILD_STARTED == "build_started"

    @pytest.mark.smoke
    def test_feature_planned_creates_with_required_fields(self) -> None:
        """FeaturePlannedPayload creates with feature_id, wave_count, task_count, waves."""
        payload = _make_feature_planned()
        assert payload.feature_id == "FEAT-001"
        assert payload.wave_count == 1
        assert payload.task_count == 2
        assert len(payload.waves) == 1

    @pytest.mark.smoke
    def test_build_progress_creates_with_required_fields(self) -> None:
        """BuildProgressPayload creates with wave, wave_total, overall_progress_pct."""
        payload = _make_build_progress(wave=2, wave_total=3, overall_progress_pct=66.7)
        assert payload.wave == 2
        assert payload.wave_total == 3
        assert payload.overall_progress_pct == pytest.approx(66.7)

    @pytest.mark.smoke
    def test_build_complete_creates_with_required_fields(self) -> None:
        """BuildCompletePayload creates with tasks_completed/failed/total and optional pr_url."""
        payload = _make_build_complete(pr_url="https://github.com/org/repo/pull/42")
        assert payload.tasks_completed == 5
        assert payload.tasks_failed == 0
        assert payload.tasks_total == 5
        assert payload.pr_url == "https://github.com/org/repo/pull/42"

    @pytest.mark.smoke
    def test_build_complete_pr_url_defaults_to_none(self) -> None:
        """BuildCompletePayload pr_url defaults to None."""
        payload = _make_build_complete()
        assert payload.pr_url is None

    @pytest.mark.smoke
    def test_approval_request_creates_with_risk_level_and_timeout(self) -> None:
        """ApprovalRequestPayload creates with risk_level 'high', timeout_seconds defaults 300."""
        payload = _make_approval_request(risk_level="high")
        assert payload.risk_level == "high"
        assert payload.timeout_seconds == 300  # noqa: PLR2004

    @pytest.mark.smoke
    def test_intent_classified_creates_with_confidence_and_target(self) -> None:
        """IntentClassifiedPayload creates with confidence 0.92, target_agent."""
        payload = _make_intent_classified(confidence=0.92, target_agent="product-owner-agent")
        assert payload.confidence == pytest.approx(0.92)
        assert payload.target_agent == "product-owner-agent"

    @pytest.mark.smoke
    def test_agent_manifest_creates_with_agent_id_and_intents(self) -> None:
        """AgentManifest creates with agent_id 'product-owner-agent', intents list."""
        payload = _make_agent_manifest()
        assert payload.agent_id == "product-owner-agent"
        assert len(payload.intents) == 1
        assert payload.intents[0].pattern == "software.*"

    @pytest.mark.smoke
    def test_dispatch_creates_with_required_fields(self) -> None:
        """DispatchPayload creates with target_agent, intent, correlation_id."""
        payload = _make_dispatch()
        assert payload.target_agent == "product-owner-agent"
        assert payload.intent == "software.build"
        assert payload.correlation_id == "corr-001"


# ===================================================================
# BOUNDARY TESTS (14 @boundary)
# ===================================================================


class TestBoundary:
    """Boundary condition tests."""

    @pytest.mark.boundary
    def test_build_id_matches_pattern(self) -> None:
        """build_id matches pattern build-{feature_id}-{YYYYMMDDHHMMSS}."""
        payload = BuildStartedPayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            wave_total=3,
        )
        pattern = r"^build-.+-\d{14}$"
        assert re.match(pattern, payload.build_id)

    @pytest.mark.boundary
    @pytest.mark.parametrize("pct", [0.0, 50.0, 100.0])
    def test_overall_progress_pct_valid_values(self, pct: float) -> None:
        """overall_progress_pct valid at 0.0, 50.0, 100.0."""
        payload = _make_build_progress(overall_progress_pct=pct)
        assert payload.overall_progress_pct == pytest.approx(pct)

    @pytest.mark.boundary
    def test_overall_progress_pct_rejects_100_1(self) -> None:
        """overall_progress_pct rejects 100.1 (ValidationError)."""
        with pytest.raises(ValidationError):
            _make_build_progress(overall_progress_pct=100.1)

    @pytest.mark.boundary
    def test_overall_progress_pct_rejects_negative(self) -> None:
        """overall_progress_pct rejects -0.1 (ValidationError)."""
        with pytest.raises(ValidationError):
            _make_build_progress(overall_progress_pct=-0.1)

    @pytest.mark.boundary
    @pytest.mark.parametrize("conf", [0.0, 0.5, 1.0])
    def test_intent_capability_confidence_valid_values(self, conf: float) -> None:
        """IntentCapability.confidence valid at 0.0, 0.5, 1.0."""
        cap = IntentCapability(pattern="test.*", confidence=conf, description="test")
        assert cap.confidence == pytest.approx(conf)

    @pytest.mark.boundary
    def test_intent_capability_confidence_rejects_1_01(self) -> None:
        """IntentCapability.confidence rejects 1.01 (ValidationError)."""
        with pytest.raises(ValidationError):
            IntentCapability(pattern="test.*", confidence=1.01, description="test")

    @pytest.mark.boundary
    def test_intent_capability_confidence_rejects_negative(self) -> None:
        """IntentCapability.confidence rejects -0.01 (ValidationError)."""
        with pytest.raises(ValidationError):
            IntentCapability(pattern="test.*", confidence=-0.01, description="test")

    @pytest.mark.boundary
    def test_intent_classified_confidence_rejects_1_5(self) -> None:
        """IntentClassifiedPayload.confidence rejects 1.5 (ValidationError)."""
        with pytest.raises(ValidationError):
            _make_intent_classified(confidence=1.5)

    @pytest.mark.boundary
    @pytest.mark.parametrize("state", ["running", "idle", "awaiting_approval", "error", "paused"])
    def test_agent_status_accepts_valid_states(self, state: str) -> None:
        """AgentStatusPayload accepts state in valid set."""
        payload = _make_agent_status(state=state)
        assert payload.state == state

    @pytest.mark.boundary
    @pytest.mark.parametrize("level", ["low", "medium", "high"])
    def test_approval_request_accepts_valid_risk_levels(self, level: str) -> None:
        """ApprovalRequestPayload accepts risk_level in {'low','medium','high'}."""
        payload = _make_approval_request(risk_level=level)
        assert payload.risk_level == level

    @pytest.mark.boundary
    @pytest.mark.parametrize("decision", ["approve", "reject", "defer", "override"])
    def test_approval_response_accepts_valid_decisions(self, decision: str) -> None:
        """ApprovalResponsePayload accepts decision in valid set."""
        payload = ApprovalResponsePayload(
            request_id="REQ-001", decision=decision, decided_by="human"
        )
        assert payload.decision == decision

    @pytest.mark.boundary
    @pytest.mark.parametrize("status", ["ready", "busy", "degraded", "draining"])
    def test_agent_heartbeat_accepts_valid_statuses(self, status: str) -> None:
        """AgentHeartbeatPayload accepts status in valid set."""
        payload = _make_agent_heartbeat(status=status)
        assert payload.status == status

    @pytest.mark.boundary
    @pytest.mark.parametrize("status", ["ready", "starting", "degraded"])
    def test_agent_manifest_accepts_valid_statuses(self, status: str) -> None:
        """AgentManifest accepts status in {'ready','starting','degraded'}."""
        payload = _make_agent_manifest(status=status)
        assert payload.status == status

    @pytest.mark.boundary
    def test_agent_manifest_rejects_max_concurrent_zero(self) -> None:
        """AgentManifest rejects max_concurrent=0 (ValidationError, ge=1)."""
        with pytest.raises(ValidationError):
            _make_agent_manifest(max_concurrent=0)


# ===================================================================
# NEGATIVE TESTS (8 @negative)
# ===================================================================


class TestNegative:
    """Negative / invalid-input tests."""

    @pytest.mark.negative
    def test_agent_status_rejects_sleeping(self) -> None:
        """AgentStatusPayload rejects state 'sleeping' (ValidationError)."""
        with pytest.raises(ValidationError):
            _make_agent_status(state="sleeping")

    @pytest.mark.negative
    def test_approval_request_rejects_critical(self) -> None:
        """ApprovalRequestPayload rejects risk_level 'critical' (ValidationError)."""
        with pytest.raises(ValidationError):
            _make_approval_request(risk_level="critical")

    @pytest.mark.negative
    def test_approval_response_rejects_ignore(self) -> None:
        """ApprovalResponsePayload rejects decision 'ignore' (ValidationError)."""
        with pytest.raises(ValidationError):
            ApprovalResponsePayload(request_id="REQ-001", decision="ignore", decided_by="human")

    @pytest.mark.negative
    def test_agent_heartbeat_rejects_offline(self) -> None:
        """AgentHeartbeatPayload rejects status 'offline' (ValidationError)."""
        with pytest.raises(ValidationError):
            _make_agent_heartbeat(status="offline")

    @pytest.mark.negative
    def test_feature_planned_requires_feature_id(self) -> None:
        """FeaturePlannedPayload requires feature_id (ValidationError on omission)."""
        with pytest.raises(ValidationError):
            FeaturePlannedPayload(
                wave_count=1,
                task_count=1,
                waves=[_make_wave_summary()],
            )  # type: ignore[call-arg]

    @pytest.mark.negative
    def test_build_complete_requires_build_id(self) -> None:
        """BuildCompletePayload requires build_id (ValidationError on omission)."""
        with pytest.raises(ValidationError):
            BuildCompletePayload(
                feature_id="FEAT-001",
                tasks_completed=5,
                tasks_failed=0,
                tasks_total=5,
                duration_seconds=120,
                summary="done",
            )  # type: ignore[call-arg]

    @pytest.mark.negative
    def test_agent_manifest_requires_agent_id(self) -> None:
        """AgentManifest requires agent_id (ValidationError on omission)."""
        with pytest.raises(ValidationError):
            AgentManifest(
                name="Test Agent",
                template="test",
            )  # type: ignore[call-arg]

    @pytest.mark.negative
    def test_dispatch_requires_target_agent(self) -> None:
        """DispatchPayload requires target_agent (ValidationError on omission)."""
        with pytest.raises(ValidationError):
            DispatchPayload(
                intent="software.build",
                input_text="build it",
                correlation_id="corr-001",
            )  # type: ignore[call-arg]


# ===================================================================
# EDGE-CASE TESTS (14 @edge_case)
# ===================================================================


class TestEdgeCase:
    """Edge-case and unusual-input tests."""

    @pytest.mark.edge_case
    def test_no_untyped_dict_any_top_level_fields(self) -> None:
        """No payload class has an untyped dict[str, Any] as a top-level field.

        Exception: ApprovalRequestPayload.details is acceptable per spec.
        """
        all_payload_classes: list[tuple[str, type[BaseModel]]] = [
            ("FeaturePlannedPayload", FeaturePlannedPayload),
            ("FeatureReadyForBuildPayload", FeatureReadyForBuildPayload),
            ("BuildStartedPayload", BuildStartedPayload),
            ("BuildProgressPayload", BuildProgressPayload),
            ("BuildCompletePayload", BuildCompletePayload),
            ("BuildFailedPayload", BuildFailedPayload),
            ("AgentStatusPayload", AgentStatusPayload),
            ("ApprovalRequestPayload", ApprovalRequestPayload),
            ("ApprovalResponsePayload", ApprovalResponsePayload),
            ("CommandPayload", CommandPayload),
            ("ResultPayload", ResultPayload),
            ("IntentClassifiedPayload", IntentClassifiedPayload),
            ("DispatchPayload", DispatchPayload),
            ("AgentResultPayload", AgentResultPayload),
            ("NotificationPayload", NotificationPayload),
            ("AgentHeartbeatPayload", AgentHeartbeatPayload),
            ("AgentDeregistrationPayload", AgentDeregistrationPayload),
            ("AgentManifest", AgentManifest),
        ]
        # Allowed exceptions: fields explicitly documented as dict[str, Any]
        allowed_dict_fields = {
            ("ApprovalRequestPayload", "details"),
            ("CommandPayload", "args"),
            ("ResultPayload", "result"),
            ("AgentResultPayload", "result"),
            ("DispatchPayload", "context"),
            ("AgentHeartbeatPayload", "metadata"),
        }
        for class_name, cls in all_payload_classes:
            for field_name, field_info in cls.model_fields.items():
                annotation = field_info.annotation
                # Check if the raw annotation is dict[str, Any]
                origin = getattr(annotation, "__origin__", None)
                if origin is dict:
                    args = getattr(annotation, "__args__", ())
                    if args == (str, Any):
                        assert (class_name, field_name) in allowed_dict_fields, (
                            f"{class_name}.{field_name} is dict[str, Any] but not in allowed list"
                        )

    @pytest.mark.edge_case
    def test_json_round_trip_fidelity_all_payload_classes(self) -> None:
        """JSON round-trip fidelity for all payload classes."""
        payloads: list[BaseModel] = [
            _make_feature_planned(),
            FeatureReadyForBuildPayload(
                feature_id="FEAT-001",
                spec_path="/specs/feat-001.yaml",
                plan_path="/plans/feat-001.md",
                pipeline_type="greenfield",
            ),
            BuildStartedPayload(
                feature_id="FEAT-001",
                build_id="build-FEAT-001-20260408120000",
                wave_total=3,
            ),
            _make_build_progress(),
            _make_build_complete(),
            BuildFailedPayload(
                feature_id="FEAT-001",
                build_id="build-FEAT-001-20260408120000",
                failure_reason="Compilation error",
                recoverable=True,
            ),
            _make_agent_status(),
            _make_approval_request(),
            ApprovalResponsePayload(request_id="REQ-001", decision="approve", decided_by="human"),
            CommandPayload(command="deploy", args={"env": "staging"}),
            ResultPayload(command="deploy", result={"status": "ok"}, success=True),
            _make_intent_classified(),
            _make_dispatch(),
            AgentResultPayload(
                agent_id="test-agent",
                intent="software.build",
                result={"output": "done"},
                correlation_id="corr-001",
                success=True,
            ),
            NotificationPayload(message="Build complete", adapter="slack"),
            _make_agent_heartbeat(),
            AgentDeregistrationPayload(agent_id="test-agent"),
            _make_agent_manifest(),
        ]
        for payload in payloads:
            dumped = payload.model_dump(mode="json")
            restored = type(payload).model_validate(dumped)
            assert restored == payload, f"Round-trip failed for {type(payload).__name__}"

    @pytest.mark.edge_case
    def test_default_values(self) -> None:
        """Default values: timeout=300, max_concurrent=1, status=ready, reason=shutdown."""
        approval = _make_approval_request()
        assert approval.timeout_seconds == 300  # noqa: PLR2004

        manifest = _make_agent_manifest()
        assert manifest.max_concurrent == 1
        assert manifest.status == "ready"

        dereg = AgentDeregistrationPayload(agent_id="test-agent")
        assert dereg.reason == "shutdown"

    @pytest.mark.edge_case
    def test_build_failed_carries_recoverable_and_failure_reason(self) -> None:
        """BuildFailedPayload carries recoverable flag and failure_reason."""
        payload = BuildFailedPayload(
            feature_id="FEAT-001",
            build_id="build-FEAT-001-20260408120000",
            failure_reason="Out of memory",
            recoverable=False,
        )
        assert payload.failure_reason == "Out of memory"
        assert payload.recoverable is False

    @pytest.mark.edge_case
    def test_nested_model_validation_invalid_wave_summary(self) -> None:
        """Nested model validation: invalid WaveSummary inside FeaturePlannedPayload raises."""
        with pytest.raises(ValidationError):
            FeaturePlannedPayload(
                feature_id="FEAT-001",
                wave_count=1,
                task_count=1,
                waves=[{"wave_number": -1, "task_count": 0, "task_ids": []}],  # type: ignore[list-item]
            )

    @pytest.mark.edge_case
    def test_extra_ignore_on_build_complete(self) -> None:
        """extra='ignore': unknown field on BuildCompletePayload silently discarded."""
        data = {
            "feature_id": "FEAT-001",
            "build_id": "build-FEAT-001-20260408120000",
            "tasks_completed": 5,
            "tasks_failed": 0,
            "tasks_total": 5,
            "duration_seconds": 120,
            "summary": "done",
            "unknown_field": "should be ignored",
        }
        payload = BuildCompletePayload(**data)
        assert not hasattr(payload, "unknown_field")

    @pytest.mark.edge_case
    def test_intent_capability_missing_pattern_raises(self) -> None:
        """IntentCapability missing pattern raises ValidationError."""
        with pytest.raises(ValidationError):
            IntentCapability(description="test")  # type: ignore[call-arg]

    @pytest.mark.edge_case
    def test_agent_heartbeat_rejects_negative_queue_depth(self) -> None:
        """AgentHeartbeatPayload rejects queue_depth=-1."""
        with pytest.raises(ValidationError):
            _make_agent_heartbeat(queue_depth=-1)

    @pytest.mark.edge_case
    def test_agent_heartbeat_rejects_negative_active_tasks(self) -> None:
        """AgentHeartbeatPayload rejects active_tasks=-1."""
        with pytest.raises(ValidationError):
            _make_agent_heartbeat(active_tasks=-1)

    @pytest.mark.edge_case
    def test_agent_status_long_task_description_accepted(self) -> None:
        """AgentStatusPayload with 10001-char task_description is accepted (no max_length)."""
        long_desc = "x" * 10001
        payload = _make_agent_status(task_description=long_desc)
        assert len(payload.task_description) == 10001  # type: ignore[arg-type]

    @pytest.mark.edge_case
    def test_agent_manifest_rejects_invalid_agent_id_format(self) -> None:
        """AgentManifest rejects agent_id='Invalid Agent ID!' (kebab-case regex)."""
        with pytest.raises(ValidationError):
            _make_agent_manifest(agent_id="Invalid Agent ID!")

    @pytest.mark.edge_case
    def test_build_progress_rejects_wave_exceeding_wave_total(self) -> None:
        """BuildProgressPayload rejects wave=5, wave_total=3 (wave > wave_total)."""
        with pytest.raises(ValidationError):
            _make_build_progress(wave=5, wave_total=3)

    @pytest.mark.edge_case
    def test_two_agent_manifests_same_agent_id_both_valid(self) -> None:
        """Two AgentManifest payloads with same agent_id are both individually valid."""
        m1 = _make_agent_manifest(agent_id="shared-agent")
        m2 = _make_agent_manifest(agent_id="shared-agent", name="Different Name")
        assert m1.agent_id == m2.agent_id == "shared-agent"

    @pytest.mark.edge_case
    def test_build_complete_rejects_tasks_sum_mismatch(self) -> None:
        """BuildCompletePayload rejects tasks_completed=8, tasks_failed=1, tasks_total=10."""
        with pytest.raises(ValidationError):
            BuildCompletePayload(
                feature_id="FEAT-001",
                build_id="build-FEAT-001-20260408120000",
                tasks_completed=8,
                tasks_failed=1,
                tasks_total=10,
                duration_seconds=120,
                summary="mismatch",
            )

    @pytest.mark.edge_case
    def test_feature_planned_rejects_wave_count_mismatch(self) -> None:
        """FeaturePlannedPayload rejects wave_count=3 with only 2 WaveSummary entries."""
        with pytest.raises(ValidationError):
            FeaturePlannedPayload(
                feature_id="FEAT-001",
                wave_count=3,
                task_count=4,
                waves=[
                    _make_wave_summary(wave_number=1),
                    _make_wave_summary(wave_number=2),
                ],
            )


# ===================================================================
# SEAM TESTS (4 @seam — integration contract verification)
# ===================================================================


class TestSeam:
    """Seam tests: verify payload class module contracts from TASK-ETS1-4."""

    @pytest.mark.seam
    def test_pipeline_payload_classes_registered(self) -> None:
        """Verify all pipeline EventType members are registered in the dispatcher.

        Contract: all pipeline payload classes must be importable from nats_core.events
        and registered against their EventType enum member.
        Producer: TASK-ETS1
        """
        pipeline_event_types = [
            EventType.FEATURE_PLANNED,
            EventType.FEATURE_READY_FOR_BUILD,
            EventType.BUILD_STARTED,
            EventType.BUILD_PROGRESS,
            EventType.BUILD_COMPLETE,
            EventType.BUILD_FAILED,
        ]
        for et in pipeline_event_types:
            cls = payload_class_for_event_type(et)
            assert cls is not None, f"No payload class registered for {et}"
            assert hasattr(cls, "model_fields"), f"{et}: not a Pydantic model"

    @pytest.mark.seam
    def test_agent_payload_classes_registered(self) -> None:
        """Verify all agent EventType members are registered in the dispatcher.

        Contract: all agent payload classes must be importable from nats_core.events
        and registered against their EventType enum member.
        Producer: TASK-ETS2
        """
        agent_event_types = [
            EventType.STATUS,
            EventType.APPROVAL_REQUEST,
            EventType.APPROVAL_RESPONSE,
            EventType.COMMAND,
            EventType.RESULT,
            EventType.ERROR,
        ]
        for et in agent_event_types:
            cls = payload_class_for_event_type(et)
            assert cls is not None, f"No payload class registered for {et}"
            assert hasattr(cls, "model_fields"), f"{et}: not a Pydantic model"

    @pytest.mark.seam
    def test_jarvis_payload_classes_registered(self) -> None:
        """Verify all Jarvis EventType members are registered in the dispatcher.

        Contract: all Jarvis payload classes must be importable from nats_core.events
        and registered against their EventType enum member.
        Producer: TASK-ETS3
        """
        jarvis_event_types = [
            EventType.INTENT_CLASSIFIED,
            EventType.DISPATCH,
            EventType.AGENT_RESULT,
            EventType.NOTIFICATION,
        ]
        for et in jarvis_event_types:
            cls = payload_class_for_event_type(et)
            assert cls is not None, f"No payload class registered for {et}"
            assert hasattr(cls, "model_fields"), f"{et}: not a Pydantic model"

    @pytest.mark.seam
    def test_fleet_payload_classes_registered(self) -> None:
        """Verify all fleet EventType members are registered in the dispatcher.

        Contract: AgentManifest registered for AGENT_REGISTER; fleet payloads
        for heartbeat/deregister.
        Producer: TASK-ETS4
        """
        fleet_event_types = [
            EventType.AGENT_REGISTER,
            EventType.AGENT_HEARTBEAT,
            EventType.AGENT_DEREGISTER,
        ]
        for et in fleet_event_types:
            cls = payload_class_for_event_type(et)
            assert cls is not None, f"No payload class registered for {et}"
            assert hasattr(cls, "model_fields"), f"{et}: not a Pydantic model"


# ===================================================================
# DISPATCHER-SPECIFIC TESTS
# ===================================================================


class TestDispatcher:
    """Tests specific to the payload_class_for_event_type dispatcher."""

    @pytest.mark.smoke
    def test_dispatcher_returns_correct_type_for_feature_planned(self) -> None:
        """Dispatcher returns FeaturePlannedPayload for FEATURE_PLANNED."""
        assert payload_class_for_event_type(EventType.FEATURE_PLANNED) is FeaturePlannedPayload

    @pytest.mark.smoke
    def test_dispatcher_returns_correct_type_for_build_complete(self) -> None:
        """Dispatcher returns BuildCompletePayload for BUILD_COMPLETE."""
        assert payload_class_for_event_type(EventType.BUILD_COMPLETE) is BuildCompletePayload

    @pytest.mark.smoke
    def test_dispatcher_returns_agent_manifest_for_agent_register(self) -> None:
        """Dispatcher returns AgentManifest for AGENT_REGISTER."""
        assert payload_class_for_event_type(EventType.AGENT_REGISTER) is AgentManifest

    @pytest.mark.smoke
    def test_dispatcher_returns_agent_status_for_error(self) -> None:
        """ERROR event type maps to AgentStatusPayload (reused per spec)."""
        assert payload_class_for_event_type(EventType.ERROR) is AgentStatusPayload

    @pytest.mark.negative
    def test_dispatcher_registry_is_module_level_dict(self) -> None:
        """Registry is a module-level dict[EventType, type[BaseModel]] constant."""
        from nats_core import envelope

        assert hasattr(envelope, "_EVENT_TYPE_REGISTRY")
        registry = envelope._EVENT_TYPE_REGISTRY
        assert isinstance(registry, dict)
        assert len(registry) == 19  # noqa: PLR2004
        for key, value in registry.items():
            assert isinstance(key, EventType)
            assert issubclass(value, BaseModel)
